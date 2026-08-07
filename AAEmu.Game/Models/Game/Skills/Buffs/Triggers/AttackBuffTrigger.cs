using System;
using System.Linq;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    public class AttackBuffTrigger : BuffTrigger
    {
        private const uint WeaponPoisonBuffTag = 3567;

        public override void Execute(object sender, EventArgs eventArgs)
        {
            var args = eventArgs as OnAttackArgs;
            _log.Trace("Buff[{0}] {1} executed. Applying {2}[{3}]!", _buff.Template.BuffId, this.GetType().Name, Template.Effect.GetType().Name, Template.Effect.Id);
            //Template.Effect.Apply()

            if (!(_owner is Unit owner))
            {
                _log.Warn("AttackTrigger owner is not a Unit");
                return;   
            }

            if (args?.Attacker == null || args.Target == null)
                return;

            // AA8 preserves this family tag on the base and ancestral
            // Poisoned Weapons buffs while omitting the server-side trigger row.
            var isWeaponPoison = SkillManager.Instance
                .GetBuffTags(_buff.Template.BuffId)
                .Contains(WeaponPoisonBuffTag);
            if (isWeaponPoison && !IsSuccessfulWeaponHit(args))
                return;

            ApplyResolved(args.Attacker, args.Target, 0);
            if (isWeaponPoison)
                _buff.Exit();
            else if (_buff.Template.RemoveOnAttackBuffTrigger)
                owner.Buffs.TriggerRemoveOn(BuffRemoveOn.AttackBuffTrigger);
        }

        public static bool IsSuccessfulWeaponHit(OnAttackArgs args)
        {
            return args != null
                && args.Amount > 0
                && (args.DamageType == DamageType.Melee || args.DamageType == DamageType.Ranged);
        }

        public AttackBuffTrigger(Buff owner, BuffTriggerTemplate template) : base(owner, template)
        {

        }
    }
}
