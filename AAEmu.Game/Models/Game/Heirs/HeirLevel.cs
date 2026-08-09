namespace AAEmu.Game.Models.Game.Heirs
{
    public sealed class HeirLevel
    {
        public uint Id { get; set; }
        public byte Level { get; set; }
        public int ReqItemCount { get; set; }
        public uint ReqItemId { get; set; }
        public long ReqTotalExp { get; set; }
        public byte Step { get; set; }
    }
}
