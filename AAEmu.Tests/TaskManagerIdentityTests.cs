using AAEmu.Game.Core.Managers;
using Xunit;

namespace AAEmu.Tests
{
    public class TaskManagerIdentityTests
    {
        [Fact]
        public void RecycledTaskIdStillProducesUniqueQuartzIdentity()
        {
            const string taskName = "DispelTask";
            const uint recycledTaskId = 396884;

            var first = TaskManager.BuildSchedulerIdentity(taskName, recycledTaskId, 41);
            var second = TaskManager.BuildSchedulerIdentity(taskName, recycledTaskId, 42);

            Assert.Equal("DispelTask396884-41", first);
            Assert.Equal("DispelTask396884-42", second);
            Assert.NotEqual(first, second);
        }
    }
}
