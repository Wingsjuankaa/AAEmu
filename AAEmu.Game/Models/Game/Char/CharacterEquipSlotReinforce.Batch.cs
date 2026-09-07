using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;

namespace AAEmu.Game.Models.Game.Char;

public sealed partial class CharacterEquipSlotReinforce
{
    private Skill _batchSkill;
    private EquipSlotReinforceBatchRequest _batchRequest;
    private readonly EquipSlotReinforceBatchTransport _batchTransport = new();

    public void ReceiveBatchFragment(string name, string password, bool create)
    {
        lock (GamePersistence.Sync)
        lock (_sync)
        {
            var request = _batchTransport.Receive(name, password, create, DateTime.UtcNow, out var cancelled);
            if (cancelled != 0) CancelBatch(cancelled);
            if (request is null) return;
            Logger.Info("Ipnya batch transport received character={0} request={1} slot={2}", owner.Id, request.RequestId, request.Slot);
            StartBatch(request);
        }
    }

    public bool StartBatch(EquipSlotReinforceBatchRequest request)
    {
        lock (GamePersistence.Sync)
        lock (_sync)
        {
            if (!IsEnabled || owner.Level < Data.MinimumLevel || owner.Hp <= 0 || request is null ||
                (_batchSkill is { Cancelled: false }) || owner.SkillTask is not null)
                return Reject();
            var plan = request.CreatePlan(Data, _state, false);
            if (plan is null || !owner.CanPayEquipSlotReinforce(plan)) return Reject();
            var template = SkillManager.Instance.GetSkillTemplate(EquipSlotReinforceBatchRequest.SkillId);
            if (template is null) return Reject();
            var skill = new Skill(template);
            var caster = new SkillCasterUnit(owner.ObjId);
            var target = new SkillCastUnitTarget(owner.ObjId);
            var context = new SkillObjectEquipSlotReinforceMaterials
            {
                Flag = SkillObjectType.EquipSlotReinforceMaterials,
                EquipSlot = request.Slot, MaterialId = request.Recipes[0].Material,
                AutoUseAaPoint = false, BatchRequest = request
            };
            _batchSkill = skill;
            _batchRequest = request;
            // One native skill lifecycle, including requirements, cooldown, animation and cancellation.
            var result = skill.Use(owner, caster, target, context, false, out var value16, out var value32);
            if (result != SkillResult.Success)
            {
                _batchSkill = null; _batchRequest = null;
                var fail = new SCSkillStartedPacket(skill.Id, 0, caster, target, skill, context);
                fail.SetSkillResult(result); fail.SetResultUShort(value16); fail.SetResultUInt(value32);
                owner.SendPacket(fail);
                Logger.Info("Ipnya batch rejected character={0} request={1} result={2}", owner.Id, request.RequestId, result);
                return false;
            }
            Logger.Info("Ipnya batch cast character={0} request={1} slot={2} gain={3} cost={4} recipes={5}",
                owner.Id, request.RequestId, request.Slot, request.GainExperience, request.Cost,
                string.Join(",", request.Recipes.Select(r => $"{r.Material}:{r.Count}")));
            return true;
        }
    }

    public bool CompleteBatch(EquipSlotReinforceBatchRequest request, Skill skill)
    {
        lock (GamePersistence.Sync)
        lock (_sync)
        {
            if (!ReferenceEquals(_batchSkill, skill) || !ReferenceEquals(_batchRequest, request) || skill.Cancelled)
                return false;
            // Consume the authorization exactly once even if payment/state validation now fails.
            _batchSkill = null; _batchRequest = null;
            return Commit(state => request.CreatePlan(Data, state, false));
        }
    }

    public void CancelBatch(uint requestId)
    {
        lock (GamePersistence.Sync)
        lock (_sync)
        {
            if (_batchRequest?.RequestId != requestId || _batchSkill is null) return;
            var skill = _batchSkill;
            _batchSkill = null; _batchRequest = null;
            skill.Cancelled = true;
            // A late cancellation must never stop another skill now owned by the character.
            if (ReferenceEquals(owner.SkillTask?.Skill, skill))
            {
                owner.SkillTask.Cancel();
                skill.Stop(owner);
            }
            Logger.Info("Ipnya batch cancelled character={0} request={1}", owner.Id, requestId);
        }
    }
}
