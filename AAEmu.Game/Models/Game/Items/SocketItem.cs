using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items
{
    /// <summary>
    /// AA8 item implementation 0x15. Gameplay installation remains governed
    /// by <see cref="Services.ItemSocketRuleService"/>.
    /// </summary>
    public sealed class SocketItem : Item
    {
        public SocketItem()
        {
        }

        public SocketItem(ulong id, ItemTemplate template, int count)
            : base(id, template, count)
        {
        }
    }
}
