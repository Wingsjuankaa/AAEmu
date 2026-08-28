using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Static;

using NLog;

namespace AAEmu.Game.Models.Game.Housing;

public static class HousingBindingRuntime
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

    public static bool TryGetDefinition(
        House house,
        uint doodadId,
        AttachPointKind attachPoint,
        out HousingBindingDefinition definition)
    {
        definition = house?.Template?.HousingBindings.FirstOrDefault(x =>
            x.DoodadId == doodadId && x.AttachPointId == attachPoint);
        return definition != null;
    }

    public static bool AdoptPersistentBinding(House house, Doodad doodad)
    {
        if (!TryGetDefinition(house, doodad.TemplateId, doodad.AttachPoint, out var definition) ||
            !definition.IsExecutable ||
            !definition.ForceDbSave)
            return false;

        Configure(house, doodad, definition);
        if (!house.AttachedDoodads.Contains(doodad))
            house.AttachedDoodads.Add(doodad);
        return true;
    }

    public static bool IsCatalogBinding(House house, Doodad doodad) =>
        TryGetDefinition(house, doodad.TemplateId, doodad.AttachPoint, out _);

    public static void Synchronize(House house, bool spawn)
    {
        if (house?.Template == null)
            return;

        if (house.CurrentStep != -1)
        {
            RemoveBindings(house);
            return;
        }

        foreach (var definition in house.Template.HousingBindings.Where(x => x.IsExecutable))
        {
            var matches = house.AttachedDoodads
                .Where(d => d.TemplateId == definition.DoodadId &&
                            d.AttachPoint == definition.AttachPointId)
                .OrderBy(d => d.DbId)
                .ThenBy(d => d.ObjId)
                .ToList();

            var doodad = matches.FirstOrDefault();
            if (doodad == null)
            {
                doodad = DoodadManager.Instance.Create(
                    house.ParentWorld, 0, definition.DoodadId, house, true);
                if (doodad == null)
                {
                    Logger.Error(
                        "Failed to materialize AA10 housing binding house={0} template={1} doodad={2} attach={3}",
                        house.Id, house.TemplateId, definition.DoodadId, definition.AttachPointId);
                    continue;
                }

                Configure(house, doodad, definition);
                doodad.IsPersistent = definition.ForceDbSave;
                doodad.InitDoodad();
                if (doodad.IsPersistent)
                    doodad.Save();
                house.AttachedDoodads.Add(doodad);
                if (spawn)
                    doodad.Spawn();
            }
            else
            {
                Configure(house, doodad, definition);
                doodad.IsPersistent = definition.ForceDbSave;
                if (spawn && !doodad.IsVisible)
                    doodad.Spawn();
            }

            foreach (var duplicate in matches.Skip(1))
            {
                Logger.Warn(
                    "Removing duplicate AA10 housing binding house={0} doodad={1} attach={2} obj={3}",
                    house.Id, definition.DoodadId, definition.AttachPointId, duplicate.ObjId);
                RemoveDoodad(house, duplicate);
            }
        }
    }

    public static void RelayToZone(House house)
    {
        if (house?.CurrentStep != -1)
            return;

        foreach (var doodad in house.AttachedDoodads
                     .Where(IsStructuralBinding)
                     .OrderBy(d => (byte)d.AttachPoint)
                     .ThenBy(d => d.TemplateId)
                     .ThenBy(d => d.ObjId))
            WorldIntegration.RelayCreateDoodadToZone?.Invoke(doodad);
    }

    public static void RemoveBindings(House house)
    {
        if (house?.AttachedDoodads == null)
            return;

        foreach (var doodad in house.AttachedDoodads.Where(IsStructuralBinding).ToArray())
            RemoveDoodad(house, doodad);
    }

    public static bool IsStructuralBinding(Doodad doodad) =>
        doodad?.ParentObj is House house &&
        TryGetDefinition(house, doodad.TemplateId, doodad.AttachPoint, out _);

    private static void Configure(
        House house,
        Doodad doodad,
        HousingBindingDefinition definition)
    {
        doodad.AttachPoint = definition.AttachPointId;
        doodad.ParentObj = house;
        doodad.ParentObjId = house.ObjId;
        doodad.OwnerDbId = house.Id;
        doodad.OwnerId = house.OwnerId;
        doodad.OwnerType = DoodadOwnerType.Housing;
        doodad.Transform = house.Transform.CloneDetached(doodad);
        doodad.Transform.Parent = house.Transform;
        doodad.Transform.Local.SetPosition(
            definition.Transform.X,
            definition.Transform.Y,
            definition.Transform.Z);
        doodad.Transform.Local.ApplyFromQuaternion(definition.Transform.Rotation);
        doodad.SetScale(definition.Transform.ScaleX);
    }

    private static void RemoveDoodad(House house, Doodad doodad)
    {
        house.AttachedDoodads.Remove(doodad);
        var objId = doodad.ObjId;
        doodad.Delete();
        if (objId > 0)
            NonUnitObjectIdManager.Instance.ReleaseId(objId);
    }
}
