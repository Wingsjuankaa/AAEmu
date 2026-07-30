using System;
using System.Linq;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Scripts.Commands
{
    public class AA8Observe : ICommand
    {
        public void OnLoad()
        {
            CommandManager.Instance.Register("aa8observe", this);
        }

        public string GetCommandLineHelp()
        {
            return "<start|status|mark|continue|stop|resume>";
        }

        public string GetCommandHelpText()
        {
            return "Controlled AA8 quest/item observation sessions.";
        }

        public void Execute(Character character, string[] args)
        {
            if (args.Length == 0)
            {
                SendUsage(character);
                return;
            }

            var service = AA8ObservationService.Instance;
            switch (args[0].ToLowerInvariant())
            {
                case "start":
                {
                    var label = Join(args, 1, "manual-test");
                    if (service.StartSession(
                            character,
                            label,
                            out var sessionId,
                            out var error))
                    {
                        character.SendMessage(
                            "[AA8Observe] Started {0}. One relevant interaction is allowed; inspect it before /aa8observe continue.",
                            sessionId);
                    }
                    else
                    {
                        character.SendMessage(
                            "[AA8Observe] Could not start: {0}.",
                            error);
                    }
                    return;
                }
                case "status":
                {
                    var status = service.GetStatus(character);
                    character.SendMessage(
                        "[AA8Observe] available={0}, active={1}, gate={2}, session={3}, last={4}, queue={5}, dropped={6}, label={7}",
                        status.Available,
                        status.Active,
                        status.GateOpen ? "open" : "paused",
                        string.IsNullOrEmpty(status.SessionId) ? "none" : status.SessionId,
                        string.IsNullOrEmpty(status.LastInteractionId) ? "none" : status.LastInteractionId,
                        status.QueueDepth,
                        status.DroppedEvents,
                        string.IsNullOrEmpty(status.Label) ? "none" : status.Label);
                    return;
                }
                case "mark":
                {
                    if (args.Length < 2 ||
                        !(args[1].Equals("ok", StringComparison.OrdinalIgnoreCase) ||
                          args[1].Equals("fail", StringComparison.OrdinalIgnoreCase)))
                    {
                        character.SendMessage(
                            "[AA8Observe] Usage: /aa8observe mark <ok|fail> <note>");
                        return;
                    }
                    var success = args[1].Equals(
                        "ok",
                        StringComparison.OrdinalIgnoreCase);
                    if (service.Mark(
                            character,
                            success,
                            Join(args, 2, string.Empty),
                            out var error))
                        character.SendMessage("[AA8Observe] Client result recorded.");
                    else
                        character.SendMessage("[AA8Observe] Could not mark: {0}.", error);
                    return;
                }
                case "continue":
                {
                    if (service.Continue(
                            character,
                            Join(args, 1, string.Empty),
                            out var error))
                        character.SendMessage("[AA8Observe] Gate opened for one interaction.");
                    else
                        character.SendMessage("[AA8Observe] Could not continue: {0}.", error);
                    return;
                }
                case "stop":
                {
                    if (service.StopSession(
                            character,
                            Join(args, 1, "manual-stop"),
                            true,
                            out var sessionId))
                        character.SendMessage("[AA8Observe] Stopped and flushed {0}.", sessionId);
                    else
                        character.SendMessage("[AA8Observe] No active session.");
                    return;
                }
                case "resume":
                {
                    if (args.Length < 2)
                    {
                        character.SendMessage(
                            "[AA8Observe] Usage: /aa8observe resume <session-id>");
                        return;
                    }
                    if (service.ResumeSession(
                            character,
                            args[1],
                            out var sessionId,
                            out var persisted,
                            out var error))
                    {
                        character.SendMessage(
                            "[AA8Observe] Resumed as {0}; persisted={1}.",
                            sessionId,
                            persisted);
                    }
                    else
                    {
                        character.SendMessage(
                            "[AA8Observe] Could not resume: {0}.",
                            error);
                    }
                    return;
                }
                default:
                    SendUsage(character);
                    return;
            }
        }

        private static string Join(
            string[] args,
            int start,
            string fallback)
        {
            if (args.Length <= start)
                return fallback;
            var value = string.Join(" ", args.Skip(start));
            return string.IsNullOrWhiteSpace(value) ? fallback : value;
        }

        private static void SendUsage(Character character)
        {
            character.SendMessage(
                "[AA8Observe] /aa8observe start <label> | status | mark <ok|fail> <note> | continue [note] | stop [note] | resume <session-id>");
        }
    }
}
