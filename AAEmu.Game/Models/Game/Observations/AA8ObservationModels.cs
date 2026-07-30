using System;

namespace AAEmu.Game.Models.Game.Observations
{
    public sealed class NativeQuestRuntimeEntry
    {
        public uint QuestId { get; set; }
        public string State { get; set; } = "absent";
        public string ReasonsJson { get; set; } = "[]";
        public string ActTypesJson { get; set; } = "[]";
        public string ItemIdsJson { get; set; } = "[]";
        public string NpcIdsJson { get; set; } = "[]";
        public string DoodadIdsJson { get; set; } = "[]";
        public string Authority { get; set; } = "unconfirmed";
    }

    public sealed class AA8ObservationStatus
    {
        public bool Available { get; set; }
        public bool Active { get; set; }
        public bool GateOpen { get; set; }
        public string SessionId { get; set; } = string.Empty;
        public string LastInteractionId { get; set; } = string.Empty;
        public string Label { get; set; } = string.Empty;
        public int QueueDepth { get; set; }
        public long DroppedEvents { get; set; }
    }

    public sealed class AA8ObservationGate
    {
        private readonly object _sync = new object();
        private bool _open = true;
        private string _currentInteractionId = string.Empty;
        private string _lastInteractionId = string.Empty;

        public bool IsOpen
        {
            get
            {
                lock (_sync)
                    return _open;
            }
        }

        public string CurrentInteractionId
        {
            get
            {
                lock (_sync)
                    return _currentInteractionId;
            }
        }

        public string LastInteractionId
        {
            get
            {
                lock (_sync)
                    return _lastInteractionId;
            }
        }

        public bool TryBegin(string interactionId)
        {
            if (string.IsNullOrWhiteSpace(interactionId))
                throw new ArgumentException("An interaction id is required.", nameof(interactionId));

            lock (_sync)
            {
                if (!_open || !string.IsNullOrEmpty(_currentInteractionId))
                    return false;
                _open = false;
                _currentInteractionId = interactionId;
                return true;
            }
        }

        public void Complete(string interactionId)
        {
            lock (_sync)
            {
                if (_currentInteractionId != interactionId)
                    return;
                _lastInteractionId = interactionId;
                _currentInteractionId = string.Empty;
            }
        }

        public bool Continue()
        {
            lock (_sync)
            {
                if (!string.IsNullOrEmpty(_currentInteractionId))
                    return false;
                _open = true;
                return true;
            }
        }
    }
}
