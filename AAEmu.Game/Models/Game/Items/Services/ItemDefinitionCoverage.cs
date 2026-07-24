using System;
using System.Threading;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public enum ItemDefinitionCoverageState
    {
        Unknown,
        CatalogOnly,
        PhaseACandidate,
        Complete,
        Blocked
    }

    public sealed class ItemDefinitionCoverage
    {
        public uint ItemId { get; set; }
        public string ConcreteType { get; set; } = "unknown";
        public ItemDefinitionCoverageState State { get; set; }
        public string MissingDependencies { get; set; } = string.Empty;
        public string Provenance { get; set; } = string.Empty;

        public bool CanCreate => State == ItemDefinitionCoverageState.Complete;
    }

    public interface IItemDefinitionCoverageService
    {
        bool NativeCatalogueAvailable { get; }
        ItemDefinitionCoverage Get(uint itemId);
        void Clear();
        void Register(ItemDefinitionCoverage coverage);
        IDisposable BeginPhaseACandidateTestCreation();
    }

    public sealed class ItemDefinitionCoverageService : IItemDefinitionCoverageService
    {
        private readonly System.Collections.Generic.Dictionary<uint, ItemDefinitionCoverage> _coverage =
            new System.Collections.Generic.Dictionary<uint, ItemDefinitionCoverage>();
        private static readonly AsyncLocal<int> PhaseACandidateTestDepth =
            new AsyncLocal<int>();

        public static ItemDefinitionCoverageService Instance { get; } = new ItemDefinitionCoverageService();
        public bool NativeCatalogueAvailable { get; private set; }
        public bool PhaseACandidateTestCreationAllowed =>
            PhaseACandidateTestDepth.Value > 0 ||
            string.Equals(
                Environment.GetEnvironmentVariable(
                    "AAEMU_ITEM8_STAGING_ALLOW_CANDIDATES"),
                "1",
                StringComparison.Ordinal);

        public ItemDefinitionCoverage Get(uint itemId)
        {
            return _coverage.TryGetValue(itemId, out var coverage)
                ? coverage
                : new ItemDefinitionCoverage { ItemId = itemId, State = ItemDefinitionCoverageState.Unknown };
        }

        public void Clear()
        {
            _coverage.Clear();
            NativeCatalogueAvailable = false;
        }

        public void Register(ItemDefinitionCoverage coverage)
        {
            if (coverage == null)
                throw new ArgumentNullException(nameof(coverage));
            _coverage[coverage.ItemId] = coverage;
            NativeCatalogueAvailable = true;
        }

        public IDisposable BeginPhaseACandidateTestCreation()
        {
            PhaseACandidateTestDepth.Value++;
            return new PhaseACandidateTestScope();
        }

        private sealed class PhaseACandidateTestScope : IDisposable
        {
            private bool _disposed;

            public void Dispose()
            {
                if (_disposed)
                    return;
                _disposed = true;
                PhaseACandidateTestDepth.Value =
                    System.Math.Max(0, PhaseACandidateTestDepth.Value - 1);
            }
        }
    }
}
