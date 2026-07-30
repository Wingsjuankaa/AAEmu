using System.Collections.Generic;
using AAEmu.Commons.Network;
using System;

namespace AAEmu.Game.Models.Game
{
    public class Configurations : PacketMarshaler
    {
        public string Key { get; set; }
        public string Value { get; set; }
    }

    public class WorldConfig
    {
        public string MOTD { get; set; } = "";
        public string LogoutMessage { get; set; } = "";
        public double AutoSaveInterval { get; set; } = 5.0;
        public double ExpRate { get; set; } = 1.0;
        public double HonorRate { get; set; } = 1.0;
        public double VocationRate { get; set; } = 1.0;
        public double LootRate { get; set; } = 1.0;
        public double GrowthRate { get; set; } = 1.0;
        public bool GodMode { get; set; } = false;
    }

    public class AA8ObservationConfig
    {
        public bool Enabled { get; set; } = true;
        public string DatabasePath { get; set; } = "Observations/aa8-runtime-observations.sqlite3";
        public int QueueCapacity { get; set; } = 10000;
        public int BatchSize { get; set; } = 100;
        public int FlushIntervalMs { get; set; } = 250;
        public int UnknownPayloadPrefixBytes { get; set; } = 256;
        public string ForensicGraphSha256 { get; set; } =
            "807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC";
    }

    public class AccountDeleteDelayTiming
    {
        public int Level { get; set; }
        public int Delay { get; set; }
    }

    public class AccountConfig
    {
        public string NameRegex { get; set; } = "^[a-zA-Z0-9]{1,18}$";
        public bool DeleteReleaseName { get; set; } = false;
        public List<AccountDeleteDelayTiming> DeleteTimings { get; set; } = new List<AccountDeleteDelayTiming>();
    }

}
