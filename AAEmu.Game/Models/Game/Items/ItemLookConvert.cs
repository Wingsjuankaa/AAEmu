namespace AAEmu.Game.Models.Game.Items
{
    public class ItemLookConvert
    {
        public uint Id { get; set; }
        public uint SlotId { get; set; }
        public int Gold { get; set; }
        public string Name { get; set; } = string.Empty;
        public uint RequiredItemId { get; set; }
        public int RequiredItemCount { get; set; }
        public uint RevertItemId { get; set; }
        public int RevertItemCount { get; set; }
    }
}
