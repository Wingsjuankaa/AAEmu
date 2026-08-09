using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class ClientDoodadTests
    {
        [Fact]
        public void ClientDoodadUsesNpcModelNormalGroupAsInitialPhase()
        {
            var doodad = new Doodad
            {
                Template = new DoodadTemplate
                {
                    ClientDoodad = true,
                    FuncGroups =
                    {
                        new DoodadFuncGroups
                        {
                            Id = 41495,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                            Model = string.Empty
                        },
                        new DoodadFuncGroups
                        {
                            Id = 41496,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                            Model = "npctype://10581"
                        }
                    }
                }
            };

            Assert.Equal(41496u, doodad.GetFuncGroupId());
        }

        [Fact]
        public void StandardDoodadStillUsesStartGroup()
        {
            var doodad = new Doodad
            {
                Template = new DoodadTemplate
                {
                    ClientDoodad = false,
                    FuncGroups =
                    {
                        new DoodadFuncGroups
                        {
                            Id = 10,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                            Model = "stone.cgf"
                        },
                        new DoodadFuncGroups
                        {
                            Id = 11,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                            Model = "npctype://10581"
                        }
                    }
                }
            };

            Assert.Equal(10u, doodad.GetFuncGroupId());
        }

        [Fact]
        public void ClientDoodadCanUseNpcModelFromNativeStartGroup()
        {
            var doodad = new Doodad
            {
                Template = new DoodadTemplate
                {
                    ClientDoodad = true,
                    FuncGroups =
                    {
                        new DoodadFuncGroups
                        {
                            Id = 41492,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                            Model = "npctype://10646"
                        }
                    }
                }
            };

            Assert.Equal(41492u, doodad.GetFuncGroupId());
        }

        [Fact]
        public void ExplicitClientDoodadProxyPhaseWinsDuringSpawnSelection()
        {
            var doodad = new Doodad
            {
                FuncGroupId = 41603,
                Template = new DoodadTemplate
                {
                    ClientDoodad = true,
                    FuncGroups =
                    {
                        new DoodadFuncGroups
                        {
                            Id = 41579,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                            Model = "npctype://10797"
                        },
                        new DoodadFuncGroups
                        {
                            Id = 41603,
                            GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                            Model = "npctype://10797"
                        }
                    }
                }
            };

            Assert.Equal(41603u, doodad.GetFuncGroupId());
        }

        [Fact]
        public void DeferredPhaseReturnStopsAndResetsTraversalCycle()
        {
            var doodad = new Doodad();

            Assert.True(doodad.TryTrackPhaseTraversal(4257));
            Assert.True(doodad.TryTrackPhaseTraversal(4271));
            Assert.False(doodad.TryTrackPhaseTraversal(4257));
            Assert.Empty(doodad.ListGroupId);
            Assert.True(doodad.TryTrackPhaseTraversal(4257));
        }
    }
}
