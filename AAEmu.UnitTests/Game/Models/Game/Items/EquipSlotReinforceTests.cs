using System.Runtime.CompilerServices;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class EquipSlotReinforceTests
{
    private static EquipSlotReinforceGameData Catalog()
    {
        var d = new EquipSlotReinforceGameData();
        d.Levels[(0,1)] = new(0,1,100,2,0,51597,2);
        d.Levels[(0,2)] = new(0,2,200,2,1,51598,3);
        d.Levels[(0,3)] = new(0,3,0,2,2,0,0);
        d.Materials[10] = new(10,0,1,70,0,25,1);
        d.Materials[11] = new(11,0,15,700,0,25,1);
        d.MaterialSets[1] = [(51594,2)];
        d.Milestones[1] = new(1,0,2);
        d.Modifiers[100] = new(100,1,new BonusTemplate { Value = 10 },2);
        d.Modifiers[101] = new(101,1,new BonusTemplate { Value = 20 },3);
        typeof(EquipSlotReinforceGameData).GetProperty(nameof(d.RerollItem))!.SetValue(d,46682u);
        return d;
    }

    [Test]
    public async Task FeedClampsOverflowWithoutPromotingOrChangingInput()
    {
        var state = new EquipSlotReinforceState().With(0,new(1,80));
        var plan = EquipSlotReinforceCalculator.AddExperience(Catalog(),state,0,10,false);
        await Assert.That(plan.State.Get(0)).IsEqualTo(new EquipSlotReinforceProgress(1,100));
        await Assert.That(state.Get(0).Experience).IsEqualTo(80);
        await Assert.That(plan.Materials.Single()).IsEqualTo((51594u,2));
        await Assert.That(plan.Cost).IsEqualTo(25L);
        await Assert.That(EquipSlotReinforceCalculator.AddExperience(Catalog(),plan.State,0,10,false)).IsNull();
    }

    [Test]
    public async Task RejectsWrongSlotUnknownMaterialAndResidualLevel15()
    {
        var d = Catalog(); var s = new EquipSlotReinforceState();
        await Assert.That(EquipSlotReinforceCalculator.AddExperience(d,s,1,10,false)).IsNull();
        await Assert.That(EquipSlotReinforceCalculator.AddExperience(d,s,0,11,false)).IsNull();
        await Assert.That(EquipSlotReinforceCalculator.AddExperience(d,s,0,999,false)).IsNull();
        await Assert.That(EquipSlotReinforceCalculator.AddExperience(d,s.With(0,new(3,0)),0,10,false)).IsNull();
    }

    [Test]
    public async Task PromotionRequiresFullBarUsesCurrentRuneAndCannotReplay()
    {
        var d = Catalog(); var s = new EquipSlotReinforceState();
        await Assert.That(EquipSlotReinforceCalculator.LevelUp(d,s,0,_=>0)).IsNull();
        var plan = EquipSlotReinforceCalculator.LevelUp(d,s.With(0,new(1,100)),0,_=>0);
        await Assert.That(plan.Materials.Single()).IsEqualTo((51597u,2));
        await Assert.That(plan.State.Get(0)).IsEqualTo(new EquipSlotReinforceProgress(2,0));
        await Assert.That(plan.State.Effects[new(0,2)]).IsEqualTo(100u);
        await Assert.That(EquipSlotReinforceCalculator.LevelUp(d,plan.State,0,_=>0)).IsNull();
    }

    [Test]
    public async Task WeightedMilestoneIntervalsCoverEveryRoll()
    {
        var d = Catalog(); var s = new EquipSlotReinforceState().With(0,new(1,100));
        var ids = Enumerable.Range(0,5).Select(r =>
            EquipSlotReinforceCalculator.LevelUp(d,s,0,_=>r).ModifierId).ToArray();
        await Assert.That(string.Join(",",ids)).IsEqualTo("100,100,101,101,101");
    }

    [Test]
    public async Task RerollExcludesExistingEffectAsRequiredByNativeText9256()
    {
        var d=Catalog();var state=new EquipSlotReinforceState().With(0,new(2,0),new(0,2),100);
        var plan=EquipSlotReinforceCalculator.ChangeEffect(d,state,0,2,max=>max-1);
        await Assert.That(plan.ModifierId).IsEqualTo(101u);
        await Assert.That(plan.Materials.Single()).IsEqualTo((46682u,1));
        await Assert.That(state.Effects[new(0,2)]).IsEqualTo(100u);
        d.Modifiers.Remove(101);
        await Assert.That(EquipSlotReinforceCalculator.ChangeEffect(d,state,0,2,_=>0)).IsNull();
    }

    [Test]
    public async Task LockedEffectCannotReroll()
    {
        await Assert.That(EquipSlotReinforceCalculator.ChangeEffect(Catalog(),new(),0,2,_=>0)).IsNull();
    }

    [Test]
    public async Task BundlesUseBaselineOneAndAccumulateAttainedTiers()
    {
        var d = Catalog();
        d.Levels[(15,1)] = new(15,1,100,1,0,1,1);
        d.Levels[(1,1)] = new(1,1,100,3,0,1,1);
        d.Bundles.Add(new(1,1,2,1,[new BonusTemplate { Value=2000 }]));
        d.Bundles.Add(new(2,1,3,1,[new BonusTemplate { Value=750 }]));
        await Assert.That(EquipSlotReinforceCalculator.GetBonuses(d,new()).Count).IsEqualTo(0);
        var bonuses = EquipSlotReinforceCalculator.GetBonuses(d,new EquipSlotReinforceState().With(0,new(3,0)));
        await Assert.That(bonuses.Sum(x=>x.Value)).IsEqualTo(2750L);
    }

    [Test]
    public async Task InitialStateNativeGoldenBytesAndDefensiveCopy()
    {
        var slots = new Dictionary<byte,EquipSlotReinforceProgress> { [15]=new(2,0x12345678) };
        var s = new EquipSlotReinforceState(slots,new Dictionary<EquipSlotReinforceEffectKey,uint> { [new(15,2)]=0xabcdef });
        slots[15]=new(10,0);
        await Assert.That(Convert.ToHexString(s.Write(new PacketStream()).GetBytes()))
            .IsEqualTo("010000000F0000000278563412010000000F02EFCDAB00");
        await Assert.That(Convert.ToHexString(new EquipSlotReinforceState().Write(new PacketStream()).GetBytes()))
            .IsEqualTo("0000000000000000");
    }

    [Test]
    public async Task NativeProgressAndEffectPacketsGoldenBytes()
    {
        await Assert.That(SCOffsets.SCEquipSlotReinforceUpdatePacket).IsEqualTo((ushort)0x2c5);
        await Assert.That(SCOffsets.SCEquipSlotReinforceLevelEffectUpdatePacket).IsEqualTo((ushort)0x2c6);
        await Assert.That(SCOffsets.SCEquipSlotReinforceLevelEffectDeletePacket).IsEqualTo((ushort)0x2c7);
        await Assert.That(Convert.ToHexString(new SCEquipSlotReinforceUpdatePacket(0x123456,15,5,0x12345678).Write(new()).GetBytes()))
            .IsEqualTo("5634120F0578563412");
        await Assert.That(Convert.ToHexString(new SCEquipSlotReinforceLevelEffectUpdatePacket(0x123456,15,5,0xabcdef).Write(new()).GetBytes()))
            .IsEqualTo("5634120F05EFCDAB00");
        await Assert.That(Convert.ToHexString(new SCEquipSlotReinforceLevelEffectDeletePacket(0x123456,15,5).Write(new()).GetBytes()))
            .IsEqualTo("5634120F05");
    }

    [Test]
    public async Task NativeSkillContextsPreserveInputDirection()
    {
        var stream = new PacketStream(Convert.FromHexString("0F78563412015A"));
        var material = (SkillObjectEquipSlotReinforceMaterials)SkillObject.GetByType((SkillObjectType)22);
        material.Read(stream);
        await Assert.That(material.EquipSlot).IsEqualTo((byte)15);
        await Assert.That(material.MaterialId).IsEqualTo(0x12345678u);
        await Assert.That(material.AutoUseAaPoint).IsTrue();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        var effect = (SkillObjectEquipSlotReinforceEffect)SkillObject.GetByType((SkillObjectType)23);
        stream = new PacketStream(Convert.FromHexString("0F0A5A")); effect.Read(stream);
        await Assert.That(effect.EffectLevel).IsEqualTo((sbyte)10);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
    }

    private static CharacterMock CharacterWithItems(int count=5, long gold=100)
    {
        var c = new CharacterMock { Money=gold, AaPoint=70, NumInventorySlots=4 };
        var bag = new ItemContainer(0,SlotType.Inventory,false,null) { ContainerSize=4 };
        var item = new ItemMock(1,new ItemTemplate { Id=51594, MaxCount=100, FixedGrade=0 },count)
            { Slot=0,SlotType=SlotType.Inventory };
        item._holdingContainer=bag; bag.Items.Add(item); bag.UpdateFreeSlotCount();
        var inventory = (Inventory)RuntimeHelpers.GetUninitializedObject(typeof(Inventory));
        typeof(Inventory).GetProperty(nameof(Inventory.Bag))!.SetValue(inventory,bag);
        c.Inventory=inventory; return c;
    }

    [Test]
    public async Task MissingMaterialsOrCurrencyNeverCallsPersistence()
    {
        var p=EquipSlotReinforceCalculator.AddExperience(Catalog(),new(),0,10,false);
        foreach(var c in new[]{CharacterWithItems(1),CharacterWithItems(5,24)})
        {
            var called=false;
            var ok=c.TryCommitEquipSlotReinforce(p,[],[],(_,_,_)=>called=true);
            await Assert.That(ok).IsFalse(); await Assert.That(called).IsFalse();
        }
    }

    [Test]
    public async Task PersistenceFailureLeavesWalletInventoryAndTasksUntouched()
    {
        var c=CharacterWithItems(); var tasks=new List<ItemTask>(); var failed=false;
        try { c.TryCommitEquipSlotReinforce(EquipSlotReinforceCalculator.AddExperience(Catalog(),new(),0,10,false),
            tasks,[],(_,_,_)=>throw new IOException("Injected precommit failure")); }
        catch(IOException) { failed=true; }
        await Assert.That(failed).IsTrue(); await Assert.That(c.Money).IsEqualTo(100L);
        await Assert.That(c.Inventory.Bag.Items.Single().Count).IsEqualTo(5);
        await Assert.That(tasks.Count).IsEqualTo(0);
    }

    [Test]
    public async Task DurableCallbackPrecedesConsumptionAndAaPointsStaySeparate()
    {
        var c=CharacterWithItems(); var tasks=new List<ItemTask>();
        var snapshotCount=0; long persistedGold=0,persistedAa=0;
        var ok=c.TryCommitEquipSlotReinforce(EquipSlotReinforceCalculator.AddExperience(Catalog(),new(),0,10,true),
            tasks,[],(items,gold,aa)=> { snapshotCount=items.Single().Item.Count; persistedGold=gold;persistedAa=aa; });
        await Assert.That(ok).IsTrue(); await Assert.That(snapshotCount).IsEqualTo(5);
        await Assert.That(persistedGold).IsEqualTo(100L); await Assert.That(persistedAa).IsEqualTo(45L);
        await Assert.That(c.Money).IsEqualTo(100L); await Assert.That(c.AaPoint).IsEqualTo(45L);
        await Assert.That(c.Inventory.Bag.Items.Single().Count).IsEqualTo(3);
        await Assert.That(tasks.Count).IsEqualTo(2);
    }
    [Test]
    public async Task BatchPaymentAggregatesSharedItemsAndFailsAtomically()
    {
        var data=Catalog();
        data.Levels[(0,1)]=new(0,1,200,2,0,51597,2);
        data.Materials[12]=new(12,0,1,100,0,30,2);
        data.MaterialSets[2]=[(51594,1),(51602,1)];
        var request=EquipSlotReinforceBatchRequest.Parse("1,0,1,0,200,60/12:2");
        var plan=request.CreatePlan(data,new(),false);
        var c=CharacterWithItems(5,100);
        var called=false;
        await Assert.That(c.CanPayEquipSlotReinforce(plan)).IsFalse();
        await Assert.That(c.TryCommitEquipSlotReinforce(plan,[],[],(_,_,_)=>called=true)).IsFalse();
        await Assert.That(called).IsFalse();
        await Assert.That(c.Inventory.Bag.Items[0].Count).IsEqualTo(5);
        await Assert.That(c.Money).IsEqualTo(100L);
        var essence=new ItemMock(2,new ItemTemplate {Id=51602,MaxCount=100,FixedGrade=0},3)
            {Slot=1,SlotType=SlotType.Inventory,_holdingContainer=c.Inventory.Bag};
        c.Inventory.Bag.Items.Add(essence); c.Inventory.Bag.UpdateFreeSlotCount();
        await Assert.That(c.CanPayEquipSlotReinforce(plan)).IsTrue();
        await Assert.That(essence.Count).IsEqualTo(3);
        var tasks=new List<ItemTask>();
        var failed=false;
        try { c.TryCommitEquipSlotReinforce(plan,tasks,[],(_,_,_)=>throw new IOException("batch persist failure")); }
        catch(IOException) { failed=true; }
        await Assert.That(failed).IsTrue();
        await Assert.That(essence.Count).IsEqualTo(3);
        await Assert.That(c.Money).IsEqualTo(100L);
        await Assert.That(tasks.Count).IsEqualTo(0);
        await Assert.That(c.TryCommitEquipSlotReinforce(plan,tasks,[],(_,gold,_)=>
            { if(gold!=40 || essence.Count!=3) throw new Exception("premature mutation"); })).IsTrue();
        await Assert.That(essence.Count).IsEqualTo(1);
        await Assert.That(c.Inventory.Bag.Items[0].Count).IsEqualTo(3);
        await Assert.That(c.Money).IsEqualTo(40L);
        await Assert.That(tasks.Count).IsEqualTo(3);
    }

}
