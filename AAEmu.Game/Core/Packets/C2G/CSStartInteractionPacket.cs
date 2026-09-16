using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSStartInteractionPacket() : GamePacket(CSOffsets.CSStartInteractionPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var npcObjId = stream.ReadBc();
        var objId = stream.ReadBc();
        var extraInfo = stream.ReadInt32();
        var pickId = stream.ReadInt32();
        var mouseButton = stream.ReadByte();
        var modifierKeys = stream.ReadInt32();

        Logger.Warn("StartInteraction, NpcObjId: {0}, objId: {1}, extraInfo: {2}, pickId: {3}, mouse: {4}, mods: {5}",
            npcObjId, objId, extraInfo, pickId, mouseButton, modifierKeys);

        var character = Connection.ActiveChar;
        var npc = character?.ParentWorld?.GetNpc(npcObjId);
        if (npc != null)
        {
            character.CurrentInteractionObject = npc;

            // The returned skillsList is supposed to be a list of what actions you can take, and the client will
            // use the first one regardless of what you put in there.
            // Also noted is that even when you send a zero (0) skill list back (one skill of 0),
            // it will still use the first action that is prompted to the user. This effectively makes quest NPCS
            // right-clickable as intended
            // This could later be used to implement some of the anti-cheating
            // 0 is the intended default or else quests go wonky

            uint option = 0;
            if (npc.Template.TradeGoodBuy)
            {
                if (SpecialtyManager.Instance.CanStartTradeGoodInteraction(character, npc))
                    option = SkillsEnum.UseTradeGoodStore;
            }
            else if (npc.Template.Specialty)
             {
                 if (SpecialtyManager.Instance.CanStartSpecialtyInteraction(character, npc))
                     option = SkillsEnum.UseSpecialtyStore;
             }
            else
                option = NpcInteractionRules.PrimarySkill(
                    npc.Template,
                    QuestManager.Instance.IsQuestTalkNpc(npc.TemplateId));

            character.SendPacket(new SCNpcInteractionSkillListPacket(npcObjId, objId, extraInfo,
                pickId, mouseButton, modifierKeys, [option]));
        }

        var unit = Connection.ActiveChar?.ParentWorld?.GetUnit(npcObjId);
        if (unit is House house)
        {
            var buildSkillId = GetActiveHouseBuildSkillId(house);
            if (buildSkillId == 0 || !house.AllowedToInteract(Connection.ActiveChar))
            {
                Logger.Info(
                    "House interaction has no executable AA10 build step: objId={0}, design={1}, step={2}",
                    house.ObjId, house.TemplateId, house.CurrentStep);
                return;
            }

            // A foundation leaves objId at zero. The nested interaction list still needs the
            // active character as its source while the target remains the housing object.
            var sourceObjId = objId == 0 ? Connection.ActiveChar.ObjId : objId;
            Connection.ActiveChar.SendPacket(new SCWorldInteractionSkillListPacket(
                house.ObjId,
                sourceObjId,
                extraInfo,
                pickId,
                mouseButton,
                modifierKeys,
                [buildSkillId]));

            Logger.Info(
                "AA10 house build interaction list: objId={0}, design={1}, step={2}, skill={3}, source={4}",
                house.ObjId, house.TemplateId, house.CurrentStep, buildSkillId, sourceObjId);
            return;
        }

        if (unit is Mate mate)
        {
            character.SendPacket(new SCNpcInteractionSkillListPacket(npcObjId, objId, extraInfo, pickId, mouseButton, modifierKeys, [SkillsEnum.SlaveMounting]));
        }
    }

    public static uint GetActiveHouseBuildSkillId(House house)
    {
        if (house?.Template?.BuildSteps is null || house.CurrentStep < 0)
            return 0;

        return house.Template.BuildSteps.TryGetValue(house.CurrentStep, out var step)
            ? step.SkillId
            : 0;
    }
}
