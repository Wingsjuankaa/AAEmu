namespace AAEmu.Game.Models.Game.Quests
{
    /// <summary>
    /// Raw compact requirement attached to a quest component.
    /// Loading it is observational until a kind has an AA8-confirmed evaluator.
    /// </summary>
    public class QuestComponentRequirement
    {
        public uint ComponentId { get; set; }
        public bool DisplayMessage { get; set; }
        public uint KindId { get; set; }
        public uint Value1 { get; set; }
        public uint Value2 { get; set; }
        public uint Value3 { get; set; }
    }
}
