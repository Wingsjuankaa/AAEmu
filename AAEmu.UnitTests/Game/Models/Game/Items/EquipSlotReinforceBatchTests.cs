using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Network;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class EquipSlotReinforceBatchTests
{
    private static EquipSlotReinforceGameData Catalog()
    {
        var data=new EquipSlotReinforceGameData();
        data.Levels[(17,7)]=new(17,7,2400,1,0,0,0);
        data.Materials[10]=new(10,17,7,100,0,25,1);
        data.Materials[11]=new(11,17,7,175,0,35,2);
        data.Materials[12]=new(12,17,7,875,0,175,3);
        data.MaterialSets[1]=[(51594,1)];
        data.MaterialSets[2]=[(51594,1),(51602,1)];
        data.MaterialSets[3]=[(51594,5),(51602,5)];
        return data;
    }
    private static EquipSlotReinforceState State() => new EquipSlotReinforceState().With(17,new(7,0));
    private const string Quote="1,17,7,0,2450,490/12:2/11:4";

    [Test]
    public async Task RetailLuaQuotesMatchServerCatalogTotalsAcrossSlotsLevelsAndRemainders()
    {
        var root=new DirectoryInfo(AppContext.BaseDirectory);
        while(root is not null && !File.Exists(Path.Combine(root.FullName,"AAEmu.slnx"))) root=root.Parent;
        var fixtures=Path.Combine(root!.FullName,"Scripts","tests","fixtures");
        using var catalog=JsonDocument.Parse(File.ReadAllText(Path.Combine(fixtures,"ipnya_fill_exp_r575.json")));
        using var quotes=JsonDocument.Parse(File.ReadAllText(Path.Combine(fixtures,"ipnya_single_cast_quotes.json")));
        foreach(var quote in quotes.RootElement.EnumerateArray())
        {
            var source=catalog.RootElement[quote.GetProperty("fixture").GetInt32()];
            var data=new EquipSlotReinforceGameData();
            var slot=source.GetProperty("slot").GetByte();
            var level=(sbyte)source.GetProperty("level").GetInt32();
            data.Levels[(slot,level)]=new(slot,level,source.GetProperty("totalExp").GetInt32(),1,0,0,0);
            foreach(var row in source.GetProperty("recipes").EnumerateArray())
            {
                var id=row.GetProperty("materialType").GetUInt32();
                data.Materials[id]=new(id,slot,level,row.GetProperty("gainExp").GetInt32(),
                    row.GetProperty("currency").GetInt32(),row.GetProperty("currencyValue").GetInt32(),id);
                data.MaterialSets[id]=row.GetProperty("itemList").EnumerateArray().Select(item=>
                    (item.GetProperty("item").GetProperty("itemType").GetUInt32(),item.GetProperty("count").GetInt32())).ToList();
            }
            var command=quote.GetProperty("command").GetString()!;
            await Assert.That(command.Length<=233).IsTrue();
            var request=EquipSlotReinforceBatchRequest.Parse(command);
            var plan=request.CreatePlan(data,new EquipSlotReinforceState().With(slot,new(level,request.Experience)),false);
            await Assert.That(plan).IsNotNull();
            var expected=quote.GetProperty("materials").EnumerateObject().Select(item=>(uint.Parse(item.Name),item.Value.GetInt32())).ToArray();
            await Assert.That(plan.Materials.ToArray()).IsEquivalentTo(expected);
            await Assert.That(plan.Cost).IsEqualTo(request.Cost);
        }
    }

    [Test]
    public async Task SixNativeRecipesBecomeOneFullBarPlanWithAllFourteenMaterials()
    {
        var request=EquipSlotReinforceBatchRequest.Parse(Quote);
        var state=State(); var plan=request.CreatePlan(Catalog(),state,false);
        await Assert.That(plan.State.Get(17)).IsEqualTo(new EquipSlotReinforceProgress(7,2400));
        await Assert.That(plan.Cost).IsEqualTo(490L);
        await Assert.That(plan.Materials.ToArray()).IsEquivalentTo(new (uint,int)[]{(51594,14),(51602,14)});
        await Assert.That(state.Get(17).Experience).IsEqualTo(0);
        await Assert.That(request.CreatePlan(Catalog(),plan.State,false)).IsNull();
    }

    [Test]
    public async Task ParserRejectsTruncationCommandsDuplicatesAndUnboundedCounts()
    {
        foreach(var text in new[]{"", Quote+";quit", Quote+"/12:1", "1,17,7,0,2450,490/12:0",
                    "1,17,7,0,2450,490/12:101", "1,17,7,0,2450,490/12:-1", "0,17,7,0,2450,490/12:2",
                    "1,17,7,0,2450,-1/12:2", "1,17,7,0,2450,490/12:2 ", new string('1',256)})
            await Assert.That(EquipSlotReinforceBatchRequest.Parse(text)).IsNull();
    }

    [Test]
    public async Task ForgedOrStaleQuotesNeverProduceAPayment()
    {
        var request=EquipSlotReinforceBatchRequest.Parse(Quote); var data=Catalog();
        foreach(var invalid in new[]{request with{GainExperience=2400},request with{Cost=1},
                    request with{Slot=0},request with{Level=8},request with{Experience=100},
                    request with{Recipes=[new(999,14)]},request with{Recipes=[new(11,15)]},
                    request with{Recipes=[new(10,24),new(10,1)]}})
            await Assert.That(invalid.CreatePlan(data,State(),false)).IsNull();
        await Assert.That(request.CreatePlan(data,State().With(17,new(7,100)),false)).IsNull();
        data.Materials[11]=data.Materials[11] with {Currency=1};
        await Assert.That(request.CreatePlan(data,State(),false)).IsNull();
        data=Catalog(); data.MaterialSets.Remove(3);
        await Assert.That(request.CreatePlan(data,State(),false)).IsNull();
        // Extra complete recipes are forbidden even when the claimed total and price are honest.
        await Assert.That(EquipSlotReinforceBatchRequest.Parse("2,17,7,0,2625,525/11:15")
            .CreatePlan(Catalog(),State(),false)).IsNull();
    }

    [Test]
    public async Task CancellationIsCorrelatedAndLateOrReplayedEffectsCannotCommit()
    {
        var service=new CharacterEquipSlotReinforce(new CharacterMock());
        var request=EquipSlotReinforceBatchRequest.Parse(Quote);
        var skill=new Skill(new SkillTemplate {Id=EquipSlotReinforceBatchRequest.SkillId});
        void Set(string name,object value) => typeof(CharacterEquipSlotReinforce)
            .GetField(name,BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(service,value);
        Set("_batchSkill",skill); Set("_batchRequest",request);
        service.CancelBatch(2);
        await Assert.That(skill.Cancelled).IsFalse();
        await Assert.That(service.CompleteBatch(request,new Skill(new SkillTemplate()))).IsFalse();
        service.CancelBatch(1);
        await Assert.That(skill.Cancelled).IsTrue();
        await Assert.That(service.CompleteBatch(request,skill)).IsFalse();
        await Assert.That(service.CompleteBatch(request,skill)).IsFalse();
    }

    [Test]
    public async Task CustomQuoteNeverChangesNativeSkillObjectWire()
    {
        var context=new SkillObjectEquipSlotReinforceMaterials
        {
            Flag=SkillObjectType.EquipSlotReinforceMaterials, EquipSlot=17, MaterialId=12,
            BatchRequest=EquipSlotReinforceBatchRequest.Parse(Quote)
        };
        var stream=new PacketStream(); context.Write(stream);
        await Assert.That(Convert.ToHexString(stream.GetBytes())).IsEqualTo("16110C00000000");
    }
}
