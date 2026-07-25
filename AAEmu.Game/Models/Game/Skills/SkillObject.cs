using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;

namespace AAEmu.Game.Models.Game.Skills
{
    public enum SkillObjectType
    {
        None = 0,
        Unk1 = 1,
        Unk2 = 2,
        Unk3 = 3,
        Unk4 = 4,
        Unk5 = 5,
        ItemGradeEnchantingSupport = 6,
        Unk7 = 7,
        EvolvingRerollOptions = 9,
        SocketInstallOptions = 10,
        SocketChangeOptions = 11
    }

    public class SkillObject : PacketMarshaler
    {
        public SkillObjectType Flag { get; set; } = SkillObjectType.None;
        public bool Flag40 { get; set; }
        public bool Flag80 { get; set; }
        public byte InputDirection { get; set; }

        protected PacketStream WriteHeader(PacketStream stream)
        {
            var header = (byte)((byte)Flag & 0x3F);
            if (Flag40)
                header |= 0x40;
            if (Flag80)
                header |= 0x80;
            stream.Write(header);
            return stream;
        }

        protected PacketStream WriteInputDirection(PacketStream stream)
        {
            stream.Write(InputDirection);
            return stream;
        }

        public void ReadInputDirection(PacketStream stream)
        {
            InputDirection = stream.ReadByte();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            WriteInputDirection(stream);
            return stream;
        }

        public static SkillObject GetByType(SkillObjectType flag)
        {
            SkillObject obj;
            switch (flag)
            {
                case SkillObjectType.Unk1: // TODO - Skills bound to portals
                    obj = new SkillObjectUnk1();
                    break;
                case SkillObjectType.Unk2:
                    obj = new SkillObjectUnk2();
                    break;
                case SkillObjectType.Unk3:
                    obj = new SkillObjectUnk3();
                    break;
                case SkillObjectType.Unk4:
                    obj = new SkillObjectUnk4();
                    break;
                case SkillObjectType.Unk5:
                    obj = new SkillObjectUnk5();
                    break;
                case SkillObjectType.ItemGradeEnchantingSupport:
                    obj = new SkillObjectItemGradeEnchantingSupport();
                    break;
                case SkillObjectType.Unk7:
                    obj = new SkillObjectUnk7();
                    break;
                case SkillObjectType.EvolvingRerollOptions:
                    obj = new SkillObjectEvolvingRerollOptions();
                    break;
                case SkillObjectType.SocketInstallOptions:
                    obj = new SkillObjectSocketInstallOptions();
                    break;
                case SkillObjectType.SocketChangeOptions:
                    obj = new SkillObjectSocketChangeOptions();
                    break;
                default:
                    obj = new SkillObject();
                    break;
            }

            obj.Flag = flag;
            return obj;
        }
    }

    public class SkillObjectUnk1 : SkillObject
    {
        public byte Type { get; set; }
        public int Id { get; set; }
        public float X { get; set; }
        public float Y { get; set; }
        public float Z { get; set; }
        public int IndunZoneKey { get; set; }

        public override void Read(PacketStream stream)
        {
            Type = stream.ReadByte();
            Id = stream.ReadInt32();
            X = Helpers.ConvertLongX(stream.ReadInt64());
            Y = Helpers.ConvertLongX(stream.ReadInt64());
            Z = stream.ReadSingle();
            IndunZoneKey = stream.ReadInt32();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Type);
            stream.Write(Id);
            stream.Write(Helpers.ConvertLongX(X));
            stream.Write(Helpers.ConvertLongX(Y));
            stream.Write(Z);
            stream.Write(IndunZoneKey);
            WriteInputDirection(stream);
            return stream;
        }
    }
    
    public class SkillObjectUnk2 : SkillObject
    {
        public int Id { get; set; }
        public string Name { get; set; }

        public override void Read(PacketStream stream)
        {
            Id = stream.ReadInt32();
            Name = stream.ReadString();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Id);
            stream.Write(Name);
            WriteInputDirection(stream);
            return stream;
        }
    }
    
    public class SkillObjectUnk3 : SkillObject
    {
        public string Msg { get; set; }

        public override void Read(PacketStream stream)
        {
            Msg = stream.ReadString();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Msg);
            WriteInputDirection(stream);
            return stream;
        }
    }
    
    public class SkillObjectUnk4 : SkillObject
    {
        public float X { get; set; }
        public float Y { get; set; }
        public float Z { get; set; }

        public override void Read(PacketStream stream)
        {
            X = Helpers.ConvertLongX(stream.ReadInt64());
            Y = Helpers.ConvertLongY(stream.ReadInt64());
            Z = stream.ReadSingle();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Helpers.ConvertLongX(X));
            stream.Write(Helpers.ConvertLongY(Y));
            stream.Write(Z);
            WriteInputDirection(stream);
            return stream;
        }
    }
    
    public class SkillObjectUnk5 : SkillObject
    {
        public int Step { get; set; }

        public override void Read(PacketStream stream)
        {
            Step = stream.ReadInt32();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Step);
            WriteInputDirection(stream);
            return stream;
        }
    }

    public class SkillObjectUnk7 : SkillObject
    {
        public uint Id { get; set; }
        public long X { get; set; }
        public long Y { get; set; }
        public float Z { get; set; }
        public float W { get; set; }
        public int TotalTax { get; set; }

        public override void Read(PacketStream stream)
        {
            Id = stream.ReadUInt32();
            X = stream.ReadInt64();
            Y = stream.ReadInt64();
            Z = stream.ReadSingle();
            W = stream.ReadSingle();
            TotalTax = stream.ReadInt32();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Id);
            stream.Write(X);
            stream.Write(Y);
            stream.Write(Z);
            stream.Write(W);
            stream.Write(TotalTax);
            WriteInputDirection(stream);
            return stream;
        }
    }

    public class SkillObjectItemGradeEnchantingSupport : SkillObject
    {
        public ulong SupportItemId { get; set; }
        public bool AutoUseAaPoint { get; set; }

        public override void Read(PacketStream stream)
        {
            SupportItemId = stream.ReadUInt64();
            AutoUseAaPoint = stream.ReadBoolean();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(SupportItemId);
            stream.Write(AutoUseAaPoint);
            WriteInputDirection(stream);
            return stream;
        }
    }

    /// <summary>
    /// Kakao 8.0 skill-object type 9. The native evolving-reroll controller
    /// writes the zero-based physical modifier index followed by the selected
    /// replacement modifier-group id.
    /// </summary>
    public sealed class SkillObjectEvolvingRerollOptions : SkillObject
    {
        public uint ModifierIndex { get; set; }
        public uint ChangeToGroupId { get; set; }

        public override void Read(PacketStream stream)
        {
            ModifierIndex = stream.ReadUInt32();
            ChangeToGroupId = stream.ReadUInt32();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(ModifierIndex);
            stream.Write(ChangeToGroupId);
            WriteInputDirection(stream);
            return stream;
        }
    }

    /// <summary>
    /// AA8 skill-object type 10. The Gear Upgrade socket-install controller
    /// appends these values to CSStartSkill when a Lunagem/Lunascale is used
    /// as an equipment reagent.
    /// </summary>
    public class SkillObjectSocketInstallOptions : SkillObject
    {
        public bool AutoUseAaPoint { get; set; }
        public uint Count { get; set; }
        public bool Continuous { get; set; }

        public override void Read(PacketStream stream)
        {
            AutoUseAaPoint = stream.ReadBoolean();
            Count = stream.ReadUInt32();
            Continuous = stream.ReadBoolean();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(AutoUseAaPoint);
            stream.Write(Count);
            stream.Write(Continuous);
            WriteInputDirection(stream);
            return stream;
        }
    }

    /// <summary>
    /// AA8 skill-object type 11. Used by the native socket change/removal
    /// controller to identify a physical socket and whether all entries are
    /// included.
    /// </summary>
    public class SkillObjectSocketChangeOptions : SkillObject
    {
        public uint Index { get; set; }
        public bool IsAll { get; set; }

        public override void Read(PacketStream stream)
        {
            Index = stream.ReadUInt32();
            IsAll = stream.ReadBoolean();
        }

        public override PacketStream Write(PacketStream stream)
        {
            WriteHeader(stream);
            stream.Write(Index);
            stream.Write(IsAll);
            WriteInputDirection(stream);
            return stream;
        }
    }
}
