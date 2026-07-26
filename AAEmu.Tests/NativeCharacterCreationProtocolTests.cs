using System;
using System.Linq;

using AAEmu.Commons.Cryptography;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Char.Creation;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Transform;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeCharacterCreationProtocolTests
    {
        [Fact]
        public void Aa8CreateRequestUsesNativeLevelAndIntroSentinel()
        {
            Assert.Equal(1, NativeCharacterCreationCatalog.NativeLevel);
            Assert.Equal(-1, NativeCharacterCreationCatalog.NativeIntroZoneSentinel);
        }

        [Fact]
        public void Aa8ClientFramingRemovesEncryptedPadding()
        {
            // Live 0x00C capture: the encrypted body was 320 bytes, while
            // msgKey declared exactly 313 plaintext bytes. The former framing
            // leaked seven decrypted padding bytes plus one unused output byte
            // into the packet stream.
            var encryptedFrame = new byte[323];
            encryptedFrame[2] = 0x38;

            Assert.Equal(
                313,
                EncryptionManager.GetClientPlaintextLength(encryptedFrame));
            Assert.Equal(7, encryptedFrame.Length - 3 - 313);
            Assert.Equal(317, 313 + 4);
        }

        [Theory]
        [InlineData(SlotType.Inventory, 50, true, 0)]
        [InlineData(SlotType.Bank, 50, true, 0)]
        [InlineData(SlotType.Inventory, 140, true, 9)]
        [InlineData(SlotType.Inventory, 55, false, -1)]
        [InlineData(SlotType.Bank, 150, false, -1)]
        [InlineData(SlotType.Equipment, 50, false, -1)]
        public void ExpansionStepAcceptsOnlyNativeContainersAndTenSlotBoundaries(
            SlotType slotType,
            int currentSlots,
            bool expected,
            int expectedStep)
        {
            Assert.Equal(
                expected,
                Inventory.TryGetExpansionStep(slotType, currentSlots, out var step));
            Assert.Equal(expectedStep, step);
        }

        [Fact]
        public void CreateRequestGoldenPayloadIsConsumedExactly()
        {
            var body = new uint[]
            {
                0x10111213,
                0x20212223,
                0x30313233,
                0x40414243,
                0x50515253,
                0x60616263,
                0x70717273
            };
            var model = new UnitCustomModelParams(UnitCustomModelType.Face)
                .SetModelId(0x11223344);
            var output = new PacketStream();
            output.Write("Native");
            output.Write((byte)1);
            output.Write((byte)2);
            foreach (var itemId in body)
                output.Write(itemId);
            output.Write(model);
            output.Write((byte)14);
            output.Write(NativeCharacterCreationCatalog.NativeUnusedAbilitySentinel);
            output.Write(NativeCharacterCreationCatalog.NativeUnusedAbilitySentinel);
            output.Write(NativeCharacterCreationCatalog.NativeLevel);
            output.Write(NativeCharacterCreationCatalog.NativeIntroZoneSentinel);

            var bytes = output.GetBytes();
            Assert.Equal(
                new byte[] { 14, 30, 30, 1, 0xFF, 0xFF, 0xFF, 0xFF },
                bytes.Skip(bytes.Length - 8).ToArray());
            var input = (PacketStream)bytes;
            Assert.True(NativeCharacterCreationRequestWireCodec.TryRead(
                input,
                out var request,
                out var error), error);
            Assert.Equal("Native", request.Name);
            Assert.Equal(1, request.Race);
            Assert.Equal(2, request.Gender);
            Assert.Equal(body, request.Body);
            Assert.Equal(0x11223344u, request.CustomModel.ModelId);
            Assert.Equal(new byte[] { 14, 30, 30 }, request.Abilities);
            Assert.Equal(0, input.LeftBytes);
        }

        [Fact]
        public void FullActionSnapshotMatchesAa8GoldenBytes()
        {
            var slots = Enumerable.Range(0, Character.MaxActionSlots)
                .Select(_ => new ActionSlot())
                .ToArray();
            slots[1] = new ActionSlot
            {
                Type = ActionSlotType.ItemType,
                ActionId = 0x11223344
            };
            slots[2] = new ActionSlot
            {
                Type = ActionSlotType.Spell,
                ActionId = 0x55667788
            };
            slots[3] = new ActionSlot
            {
                Type = ActionSlotType.ItemId,
                ActionId = 0x0102030405060708
            };
            slots[4] = new ActionSlot
            {
                Type = ActionSlotType.RidePetSpell,
                ActionId = 0x99AABBCC
            };
            slots[5] = new ActionSlot
            {
                Type = ActionSlotType.BattlePetSpell,
                ActionId = 0xDDEEFF00
            };

            var bytes = new SCActionSlotsPacket(slots)
                .Write(new PacketStream())
                .GetBytes();

            var prefix = new byte[]
            {
                0x00,
                0x01, 0x44, 0x33, 0x22, 0x11,
                0x02, 0x88, 0x77, 0x66, 0x55,
                0x04, 0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01,
                0x05, 0xCC, 0xBB, 0xAA, 0x99,
                0x06, 0x00, 0xFF, 0xEE, 0xDD
            };
            Assert.Equal(241, bytes.Length);
            Assert.Equal(prefix, bytes.Take(prefix.Length).ToArray());
            Assert.All(bytes.Skip(prefix.Length), value => Assert.Equal(0, value));
        }

        [Fact]
        public void ActionSnapshotRejectsAnythingOtherThan217Slots()
        {
            var slots = Enumerable.Range(0, Character.MaxActionSlots - 1)
                .Select(_ => new ActionSlot())
                .ToArray();
            Assert.Throws<InvalidOperationException>(
                () => new SCActionSlotsPacket(slots).Write(new PacketStream()));
        }

        [Theory]
        [InlineData(0, 0, 0, 2)]
        [InlineData(1, 0x11223344, 0, 6)]
        [InlineData(2, 0x55667788, 0, 6)]
        [InlineData(4, 0x05060708, 0x01020304, 10)]
        [InlineData(5, 0x99AABBCC, 0, 6)]
        [InlineData(6, 0xDDEEFF00, 0, 6)]
        public void IndividualActionUpdateConsumesExactAa8Payload(
            byte rawType,
            uint low,
            uint high,
            int expectedLength)
        {
            var bytes = new PacketStream();
            bytes.Write((byte)216);
            bytes.Write(rawType);
            if (rawType == (byte)ActionSlotType.ItemId)
                bytes.Write(((ulong)high << 32) | low);
            else if (rawType != (byte)ActionSlotType.None)
                bytes.Write(low);

            var input = (PacketStream)bytes.GetBytes();
            Assert.Equal(expectedLength, input.LeftBytes);
            Assert.True(ActionSlotWireCodec.TryReadUpdate(
                input,
                out var slot,
                out var type,
                out var actionId,
                out var error), error);
            Assert.Equal(216, slot);
            Assert.Equal((ActionSlotType)rawType, type);
            Assert.Equal(((ulong)high << 32) | low, actionId);
            Assert.Equal(0, input.LeftBytes);
        }

        [Fact]
        public void IndividualActionUpdateRejectsWrongPayloadSize()
        {
            var input = (PacketStream)new byte[]
            {
                1,
                (byte)ActionSlotType.Spell,
                0x44,
                0x33,
                0x22
            };
            Assert.False(ActionSlotWireCodec.TryReadUpdate(
                input,
                out _,
                out _,
                out _,
                out _));
        }

        [Fact]
        public void Opcode0xAeIsProvenInventorySortAndExcludedFromActionBar()
        {
            Assert.Equal(0x0AE, CSOffsets.CSSortInventoryPacket);
            Assert.NotEqual(
                CSOffsets.CSSortInventoryPacket,
                CSOffsets.CSUpdateActionSlotPacket);
        }

        [Fact]
        public void CharacterDeleteResponseUsesAa8OpcodeAndPayload()
        {
            var packet = new SCCharacterDeleteResponsePacket(
                0x11223344,
                2,
                DateTime.MinValue,
                DateTime.MinValue);

            Assert.Equal(0x03D, packet.TypeId);
            Assert.Equal(5, packet.Level);

            var bytes = packet.Write(new PacketStream()).GetBytes();
            Assert.Equal(21, bytes.Length);
            Assert.Equal(
                new byte[] { 0x44, 0x33, 0x22, 0x11, 0x02 },
                bytes.Take(5).ToArray());
        }

        [Theory]
        [InlineData(false)]
        [InlineData(true)]
        public void CharacterSelectionConsumesExactAa8Payload(bool skipClientDriven)
        {
            var output = new PacketStream();
            output.Write(0x11223344u);
            output.Write(skipClientDriven);

            var bytes = output.GetBytes();
            Assert.Equal(CharacterSelectionWireCodec.PayloadSize, bytes.Length);
            Assert.Equal(
                new byte[]
                {
                    0x44, 0x33, 0x22, 0x11,
                    skipClientDriven ? (byte)1 : (byte)0
                },
                bytes);

            var input = (PacketStream)bytes;
            Assert.True(
                CharacterSelectionWireCodec.TryRead(
                    input,
                    out var characterId,
                    out var actualSkipClientDriven,
                    out var error),
                error);
            Assert.Equal(0x11223344u, characterId);
            Assert.Equal(skipClientDriven, actualSkipClientDriven);
            Assert.Equal(0, input.LeftBytes);
        }

        [Fact]
        public void CharacterSelectionRejectsHistoricalTrailingByte()
        {
            var input = (PacketStream)new byte[]
            {
                0x44, 0x33, 0x22, 0x11, 0x00, 0x00
            };

            Assert.False(
                CharacterSelectionWireCodec.TryRead(
                    input,
                    out _,
                    out _,
                    out _));
            Assert.Equal(6, input.LeftBytes);
        }

        [Fact]
        public void InSessionCharacterListHandshakeUsesAa8ZeroSentinel()
        {
            var input = (PacketStream)new byte[] { 0, 0, 0, 0 };

            Assert.True(
                CharacterListHandshakeWireCodec.TryReadReuseKeys(
                    input,
                    out var error),
                error);
            Assert.Equal(
                sizeof(uint),
                CharacterListHandshakeWireCodec.ReuseKeysPayloadSize);
            Assert.Equal(0, input.LeftBytes);
        }

        [Fact]
        public void InSessionCharacterListHandshakeRejectsHistoricalPadding()
        {
            var input = (PacketStream)new byte[6];

            Assert.False(
                CharacterListHandshakeWireCodec.TryReadReuseKeys(
                    input,
                    out _));
            Assert.Equal(6, input.LeftBytes);
        }

        [Fact]
        public void InSessionCharacterListHandshakeRejectsNonZeroSentinel()
        {
            var input = (PacketStream)new byte[] { 1, 0, 0, 0 };

            Assert.False(
                CharacterListHandshakeWireCodec.TryReadReuseKeys(
                    input,
                    out _));
            Assert.Equal(0, input.LeftBytes);
        }

        [Fact]
        public void CharacterCreationResolvesSpawnIntoTheRuntimeMainWorld()
        {
            var source = new WorldSpawnPosition
            {
                WorldId = 1,
                ZoneId = 179,
                X = 15578.042f,
                Y = 15382.122f,
                Z = 126.484f,
                Yaw = 2.1816616f
            };

            var resolved =
                NativeCharacterCreationCatalog.ResolveRuntimeSpawn(source, 0);

            Assert.Equal(1u, source.WorldId);
            Assert.Equal(0u, resolved.WorldId);
            Assert.Equal(source.ZoneId, resolved.ZoneId);
            Assert.Equal(source.X, resolved.X);
            Assert.Equal(source.Y, resolved.Y);
            Assert.Equal(source.Z, resolved.Z);
            Assert.Equal(source.Yaw, resolved.Yaw);
        }

        [Fact]
        public void CharacterResponsePreservesTheNativeModelId()
        {
            var expected = new UnitCustomModelParams(UnitCustomModelType.Skin)
                .SetCharacterIdentity(5, 2, 0x11223344)
                .SetSkinColorId(0x55667788)
                .SetBodyNormalMapId(0x99AABBCC)
                .SetBodyNormalMapWeight(0.75f);
            var input = (PacketStream)expected.Write(new PacketStream()).GetBytes();
            var actual = new UnitCustomModelParams(UnitCustomModelType.Skin);
            actual.Read(input);

            Assert.Equal(expected.ModelId, actual.ModelId);
            Assert.Equal(expected.CharRace, actual.CharRace);
            Assert.Equal(expected.CharGender, actual.CharGender);
            Assert.Equal(expected.SkinColorId, actual.SkinColorId);
            Assert.Equal(expected.BodyNormalMapId, actual.BodyNormalMapId);
            Assert.Equal(expected.BodyNormalMapWeight, actual.BodyNormalMapWeight);
            Assert.Equal(0, input.LeftBytes);
        }
    }
}
