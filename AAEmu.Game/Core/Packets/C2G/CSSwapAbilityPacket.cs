using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSSwapAbilityPacket : GamePacket
    {
        public CSSwapAbilityPacket() : base(CSOffsets.CSSwapAbilityPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var packetStart = stream.Pos;
            var packetBytes = System.BitConverter.ToString(stream.Buffer, packetStart, stream.LeftBytes);
            var objId = stream.ReadBc();
            var oldAbilityId = stream.ReadByte();
            var abilityId = stream.ReadByte();
            var auap = stream.ReadBoolean();

            var character = Connection.ActiveChar;
            if (character == null)
            {
                _log.Warn(
                    "[Ability8] Rejected swap without active character: objId={0}, old={1}, new={2}, auap={3}, payload={4}",
                    objId, oldAbilityId, abilityId, auap, packetBytes);
                return;
            }

            var npc = objId == 0 || objId == character.ObjId
                ? null
                : WorldManager.Instance.GetNpc(objId);
            var npcDistance = npc?.GetDistanceTo(character, true) ?? float.MaxValue;

            if (!IsAllowedReference(objId, character.ObjId, npc != null, npcDistance))
            {
                _log.Warn(
                    "[Ability8] Rejected swap object reference: character={0}, expectedObjId={1}, receivedObjId={2}, npc={3}, distance={4:F2}, old={5}, new={6}, auap={7}, payload={8}",
                    character.Name, character.ObjId, objId, npc?.TemplateId, npcDistance,
                    oldAbilityId, abilityId, auap, packetBytes);
                return;
            }

            if (npc != null)
            {
                _log.Info(
                    "[Ability8] NPC swap reference accepted: character={0}, npcObjId={1}, npcTemplateId={2}, distance={3:F2}",
                    character.Name, npc.ObjId, npc.TemplateId, npcDistance);
            }

            if (!character.Abilities.Swap((AbilityType)oldAbilityId, (AbilityType)abilityId))
            {
                _log.Warn(
                    "[Ability8] Rejected swap state: character={0}, old={1}, new={2}, auap={3}, active={4}/{5}/{6}, payload={7}",
                    character.Name, oldAbilityId, abilityId, auap, (byte)character.Ability1,
                    (byte)character.Ability2, (byte)character.Ability3, packetBytes);
                return;
            }

            _log.Info(
                "[Ability8] Accepted swap: character={0}, old={1}, new={2}, auap={3}, active={4}/{5}/{6}",
                character.Name, oldAbilityId, abilityId, auap, (byte)character.Ability1,
                (byte)character.Ability2, (byte)character.Ability3);
        }

        private static bool IsAllowedReference(
            uint packetObjId, uint activeObjId, bool isSpawnedNpc, float npcDistance)
        {
            // Kakao 8.0 uses zero for a direct self swap and the skill manager's
            // runtime ObjId when the same operation is submitted through an NPC.
            return packetObjId == 0 || packetObjId == activeObjId ||
                   (isSpawnedNpc && npcDistance <= 12.0f);
        }
    }
}
