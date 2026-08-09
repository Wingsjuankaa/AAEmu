using System;
using System.Collections.Generic;
using System.Text;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Buffs
{
    public class BuffEvents
    {
        public EventHandler<OnBuffStartedArgs> OnBuffStarted = delegate { };
        public EventHandler<OnDispelledArgs> OnDispelled = delegate { };
        public EventHandler<OnTimeoutArgs> OnTimeout = delegate { };
        public EventHandler<OnAbsorptionArgs> OnAbsorption = delegate { };
        public EventHandler<OnLandingArgs> OnLanding = delegate { };
        public EventHandler<OnRemoveOnMoveArgs> OnRemoveOnMove = delegate { };
    }

    public class OnBuffStartedArgs : EventArgs
    {

    }

    public class OnDispelledArgs : EventArgs
    {

    }

    public class OnTimeoutArgs : EventArgs
    {

    }

    public class OnAbsorptionArgs : EventArgs
    {
        public Unit Source { get; set; }
        public Unit Target { get; set; }
        public int Amount { get; set; }
    }

    public class OnLandingArgs : EventArgs
    {
    }

    public class OnRemoveOnMoveArgs : EventArgs
    {
    }
}
