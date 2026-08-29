using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

/// <summary>
/// Opens the client-native seed selection UI for an AA10 item-changer plot.
/// The selected item, count and skill return through CSDoodadItemChanger and
/// are validated against the plot's current phase before anything is consumed.
/// </summary>
public sealed class DoodadFuncItemChangerUiOpen : DoodadFuncTemplate
{
    public override void Use(BaseUnit caster, Doodad owner, uint skillId, int nextPhase = 0)
    {
        Logger.Trace("DoodadFuncItemChangerUiOpen: doodad={0}/{1}", owner?.ObjId, owner?.TemplateId);
    }
}
