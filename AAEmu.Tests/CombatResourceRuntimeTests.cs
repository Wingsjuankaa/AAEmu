using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Microsoft.Data.Sqlite;

using Xunit;

namespace AAEmu.Tests
{
    public class CombatResourceRuntimeTests
    {
        private static void LoadMagicSourceDescriptor(uint buffId = 0)
        {
            using var connection = new SqliteConnection("Data Source=:memory:");
            connection.Open();
            using (var command = connection.CreateCommand())
            {
                command.CommandText = @"
CREATE TABLE combat_resources (
    id INTEGER PRIMARY KEY,
    name TEXT,
    max INTEGER,
    default_point INTEGER,
    buff_id INTEGER,
    resource_buff_condition_id INTEGER,
    recovery_cycle INTEGER,
    peace_recovery_amount INTEGER,
    combat_recovery_amount INTEGER,
    etc_recovery_state_id INTEGER,
    etc_recovery_amount INTEGER,
    resouece_send_type_id INTEGER
);
CREATE TABLE combat_resource_groups (
    id INTEGER PRIMARY KEY,
    ability_id INTEGER,
    combat_resource_1_id INTEGER,
    combat_resource_2_id INTEGER,
    show_update_time_combat_resource INTEGER,
    show_update_time_transform_combat_resource INTEGER
);
INSERT INTO combat_resources VALUES
    (8, 'Magic Source', 60, 0, $buffId, 4, 1000, -1, -1, 0, 0, 1);
INSERT INTO combat_resource_groups VALUES
    (7, 7, 8, 0, 1, 0);";
                command.Parameters.AddWithValue("$buffId", buffId);
                command.ExecuteNonQuery();
            }

            CombatResourceGameData.Instance.Load(connection);
        }

        [Fact]
        public void Aa8MagicSourceDescriptorResolvesSorceryAndRetailTiming()
        {
            LoadMagicSourceDescriptor(27177);

            var resource = CombatResourceGameData.Instance.Get(8);
            Assert.NotNull(resource);
            Assert.Equal(60, resource.Max);
            Assert.Equal(27177u, resource.BuffId);
            Assert.Equal(4, resource.ResourceBuffConditionId);
            Assert.Equal(1000, resource.RecoveryCycle);
            Assert.Equal(-1, resource.PeaceRecoveryAmount);
            Assert.Equal(-1, resource.CombatRecoveryAmount);
            Assert.Equal(8u,
                CombatResourceGameData.Instance.ResolvePrimaryResourceId(AbilityType.Magic));
        }

        [Fact]
        public void MagicSourceClampsDecaysAndResetStartsAFreshCycle()
        {
            LoadMagicSourceDescriptor();
            var unit = new Unit();
            var start = new DateTime(2026, 8, 4, 12, 0, 0, DateTimeKind.Utc);

            Assert.Equal(20, unit.SetCombatResource(8, 20, true, start));
            unit.RegenerateCombatResources(start.AddMilliseconds(999));
            Assert.Equal(20, unit.GetCombatResource(8));

            unit.RegenerateCombatResources(start.AddMilliseconds(1000));
            Assert.Equal(19, unit.GetCombatResource(8));

            var reset = start.AddMilliseconds(1250);
            Assert.Equal(39, unit.SetCombatResource(8, 39, true, reset));
            unit.RegenerateCombatResources(reset.AddMilliseconds(999));
            Assert.Equal(39, unit.GetCombatResource(8));
            unit.RegenerateCombatResources(reset.AddMilliseconds(1000));
            Assert.Equal(38, unit.GetCombatResource(8));

            Assert.Equal(60, unit.SetCombatResource(8, 999, true, reset));
            Assert.Equal(0, unit.SetCombatResource(8, -999, true, reset));
        }

        [Fact]
        public void CombatResourceEffectUsesInclusiveAa8RangeAndAddsToTarget()
        {
            LoadMagicSourceDescriptor();
            var target = new Unit();
            var effect = new CombatResourceEffect
            {
                Chance = 0,
                CombatResourceId = 8,
                MinCombatResource = 20,
                MaxCombatResource = 20,
                ResetRemainTime = true
            };

            effect.Apply(target, null, target, null, null, null, null, DateTime.UtcNow);
            effect.Apply(target, null, target, null, null, null, null, DateTime.UtcNow);

            Assert.Equal(40, target.GetCombatResource(8));
        }

        [Fact]
        public void LegacyHighAbilityEffectUsesSorceryPrimaryResource()
        {
            LoadMagicSourceDescriptor();
            var target = new Unit();
            var source = new EffectSource(new Skill(new SkillTemplate
            {
                Id = 11939,
                AbilityId = (byte)AbilityType.Magic
            }));
            var effect = new HighAbilityResourceEffect
            {
                MinCombatResource = 100,
                MaxCombatResource = 100,
                ResetRemainTime = true
            };

            effect.Apply(target, null, target, null, null, source, null, DateTime.UtcNow);

            Assert.Equal(60, target.GetCombatResource(8));
        }

        [Fact]
        public void Aa8PointPacketUsesNativeLayoutAndHundredths()
        {
            var packet = new SCCombatResourcePointPacket(
                0x030201, 8, 20, 0x07060504);
            var bytes = packet.Write(new PacketStream()).GetBytes();

            Assert.Equal((ushort)0x315, packet.TypeId);
            Assert.NotEqual(SCOffsets.SCAbilitySwappedPacket, packet.TypeId);

            Assert.Equal(new byte[]
            {
                0x01, 0x02, 0x03,
                0x08, 0x00, 0x00, 0x00,
                0xD0, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x04, 0x05, 0x06, 0x07
            }, bytes);
        }

        [Fact]
        public void Aa8TransformAndUpdateTimePacketsUseNativeLayouts()
        {
            Assert.Equal((ushort)0x370, SCOffsets.SCCombatResourceTransformPacket);
            Assert.Equal((ushort)0x36E, SCOffsets.SCCombatResourceUpdateTimePacket);

            Assert.Equal(new byte[]
            {
                0x01, 0x02, 0x03,
                0x07, 0x00, 0x00, 0x00,
                0x01
            }, new SCCombatResourceTransformPacket(0x030201, 7, true)
                .Write(new PacketStream()).GetBytes());

            Assert.Equal(new byte[]
            {
                0x01, 0x02, 0x03,
                0x08, 0x00, 0x00, 0x00,
                0x01
            }, new SCCombatResourceUpdateTimePacket(0x030201, 8, true)
                .Write(new PacketStream()).GetBytes());
        }
    }
}
