using System;
using System.Threading;
using System.Threading.Tasks;
using ThreadTask = System.Threading.Tasks.Task;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Mechanics;
using NLog;
using Quartz;
using Quartz.Impl;
using Quartz.Simpl;
using Task = AAEmu.Game.Models.Tasks.Task;

namespace AAEmu.Game.Core.Managers
{
    public class TaskManager : Singleton<TaskManager>
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();

        private DefaultThreadPool _generalPool;
        private IScheduler _generalScheduler;
        private static long _schedulerSequence;

        public async void Initialize()
        {
            _generalPool = new DefaultThreadPool();
            _generalPool.MaxConcurrency = AppConfiguration.Instance.MaxConcurencyThreadPool;
            _generalPool.Initialize();

            DirectSchedulerFactory
                .Instance
                .CreateScheduler("General Scheduler", "GeneralScheduler", _generalPool, new RAMJobStore());
            _generalScheduler = await DirectSchedulerFactory.Instance.GetScheduler("General Scheduler");
        }

        public void Start()
        {
            _generalScheduler.Start();
        }

        public void Stop()
        {
            _generalScheduler.Shutdown(true);
        }

        public async void Schedule(Task task, TimeSpan? startTime = null, TimeSpan? repeatInterval = null,
            int count = -1)
        {
            var mechanicsScheduler = MechanicsRuntime.Current?.Scheduler;
            if (mechanicsScheduler != null)
            {
                mechanicsScheduler.Schedule(task, startTime, repeatInterval, count);
                return;
            }

            if (_generalScheduler.IsShutdown)
                return;

            if (task == null)
            {
                _log.Error("Task.Schedule: Task is NULL !!! StartTime: {0}, repeatInterval: {1}, count: {2}", startTime,repeatInterval, count);
                return;
            }

            task.Id = TaskIdManager.Instance.GetNextId();
            var schedulerIdentity = BuildSchedulerIdentity(
                task.Name,
                task.Id,
                Interlocked.Increment(ref _schedulerSequence));
            
            var job = JobBuilder
                .Create<TaskJob>()
                .WithIdentity(schedulerIdentity, task.Name)
                .Build();
            job.JobDataMap.Put("Logger", _log);
            job.JobDataMap.Put("Task", task);
            task.JobDetail = job;

            var triggerBuild = TriggerBuilder
                .Create()
                .WithIdentity(job.Key.Name, job.Key.Group);

            if (startTime == null)
                triggerBuild.StartNow();
            else
                triggerBuild.StartAt(DateTime.UtcNow.Add((TimeSpan) startTime));

            if (task.Scheduler == null)
            {
                triggerBuild.WithSimpleSchedule(scheduler =>
                {
                    if (repeatInterval == null)
                        return;

                    scheduler.WithInterval((TimeSpan) repeatInterval);

                    if (count > 0)
                        scheduler.WithRepeatCount(count);
                    else if (count == -1)
                        scheduler.RepeatForever();
                });
            }
            else
                triggerBuild.WithSchedule(task.Scheduler);

            task.Trigger = triggerBuild.Build();
            task.ExecuteCount = 0;
            task.MaxCount = repeatInterval == null ? 0 : count;
            task.ScheduleTime = Helpers.UnixTimeNowInMilli();

            try
            {
                await _generalScheduler.ScheduleJob(job, task.Trigger);
            }
            catch (Exception e)
            {
                _log.Error(e, "Error scheduling task");
            }
        }

        /// <summary>
        /// Builds the Quartz identity independently from the recyclable AAEmu task id.
        /// A completed one-shot job can remain observable in Quartz for a short interval
        /// after TaskIdManager releases its id. Reusing only Name+Id during that interval
        /// caused ObjectAlreadyExistsException and silently dropped Sorcery buff ticks.
        /// </summary>
        public static string BuildSchedulerIdentity(string taskName, uint taskId, long schedulerSequence)
        {
            return $"{taskName}{taskId}-{schedulerSequence}";
        }

        public async Task<bool> Cancel(Task task)
        {
            var mechanicsScheduler = MechanicsRuntime.Current?.Scheduler;
            if (mechanicsScheduler != null)
                return await mechanicsScheduler.Cancel(task);

            if (task?.JobDetail == null)
                return true;
            try
            {
                var result = await _generalScheduler.DeleteJob(task.JobDetail.Key);
                if (result)
                {
                    task.Cancelled = true;

                    TaskIdManager.Instance.ReleaseId(task.Id);
                }

                return result;
            }
            catch (SchedulerException e)
            {
                _log.Warn(e);
            }

            return task.Cancelled;
        }
    }

    [PersistJobDataAfterExecution]
    public sealed class TaskJob : IJob
    {
        public ThreadTask Execute(IJobExecutionContext context)
        {
            var log = (Logger) context.MergedJobDataMap.Get("Logger");
            try
            {
                var task = (Task) context.MergedJobDataMap.Get("Task");
                if (task.Cancelled)
                    return ThreadTask.CompletedTask;

                task.Execute();
                task.ExecuteCount++;

                if (task.MaxCount != -1 && task.ExecuteCount > task.MaxCount)
                    Clear(task.Id);
            }
            catch (Exception e)
            {
                log.Error(e);
            }

            return ThreadTask.CompletedTask;
        }

        private void Clear(uint taskId)
        {
            var thread = new Thread(id =>
                TaskIdManager.Instance.ReleaseId((uint) id)
            );
            thread.Start(taskId);
        }
    }
}
