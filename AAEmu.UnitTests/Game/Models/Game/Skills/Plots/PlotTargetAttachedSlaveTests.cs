using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Plots;

public class PlotTargetAttachedSlaveTests
{
    [Test]
    public async Task SphereCandidateMergeFindsAttachedSlaveMissingFromRegionResult()
    {
        var owner = CreateOwnerWithChild(out var child);
        var origin = new BaseUnit();
        var shape = new AreaShape { Type = AreaShapeType.Sphere, Value1 = 4f };

        var result = PlotTargetInfo.IncludeAttachedSlaveCandidates([], shape, origin, owner);

        await Assert.That(result).Count().IsEqualTo(1);
        await Assert.That(result[0]).IsSameReferenceAs(child);
    }

    [Test]
    public async Task SphereCandidateMergeStillHonorsNativeRadius()
    {
        var owner = CreateOwnerWithChild(out var child);
        child.Transform.Local.SetPosition(10f, 0f, 0f, 0f, 0f, 0f);
        var origin = new BaseUnit();
        var shape = new AreaShape { Type = AreaShapeType.Sphere, Value1 = 4f };

        var result = PlotTargetInfo.IncludeAttachedSlaveCandidates([], shape, origin, owner);

        await Assert.That(result).IsEmpty();
    }

    [Test]
    public async Task SphereCandidateMergeDoesNotDuplicateIndexedChild()
    {
        var owner = CreateOwnerWithChild(out var child);
        var origin = new BaseUnit();
        var shape = new AreaShape { Type = AreaShapeType.Sphere, Value1 = 4f };

        var result = PlotTargetInfo.IncludeAttachedSlaveCandidates([child], shape, origin, owner);

        await Assert.That(result).Count().IsEqualTo(1);
    }

    private static Slave CreateOwnerWithChild(out Slave child)
    {
        var owner = new Slave { ObjId = 100 };
        child = new Slave { ObjId = 101 };
        child.Transform.Parent = owner.Transform;
        owner.AttachedSlaves.Add(child);
        return owner;
    }
}
