using AAEmu.Commons.Network;
using AAEmu.Commons.Cryptography;
using AAEmu.Game.Core.Network.Connections;

namespace AAEmu.Game.Core.Network.Game;

public abstract class GamePacket(ushort typeId, byte level) : PacketBase<GameConnection>(typeId)
{
    public byte Level { get; set; } = level;

    /// <summary>
    /// This is called in Encode after Read() in the case of GamePackets
    /// The purpose is to separate packet data from packet behavior
    /// </summary>
    public virtual void Execute() { }

    public override PacketStream Encode()
    {
        var ps = new PacketStream();
        try
        {
            var level = Level;
            if (level == 1 && Connection.EncryptionActive)
                level = 5;

            var packet = new PacketStream()
                .Write((byte)0xdd)
                .Write(level);

            switch (level)
            {
                case 5:
                    var count = EncryptionManager.Instance.NextSCMessageCount(
                        Connection.Id, Connection.AccountId);
                    var body = new PacketStream()
                        .Write(count)
                        .Write(TypeId)
                        .Write(this);
                    var data = new PacketStream()
                        .Write(EncryptionManager.Instance.Crc8(body))
                        .Write(body, false);
                    packet.Write(EncryptionManager.Instance.StoCEncrypt(data), false);
                    break;
                case 1:
                    packet
                        .Write((byte)0)
                        .Write((byte)0)
                        .Write(TypeId)
                        .Write(this);
                    break;
                default:
                    packet.Write(TypeId).Write(this);
                    break;
            }

            ps.Write(packet);
        }
        catch (Exception ex)
        {
            Logger.Fatal(ex);
            throw;
        }

        var logString = $"GamePacket: S->C type {TypeId:X3} {ToString()?.Substring(23)}{Verbose()}";
        switch (LogLevel)
        {
            case PacketLogLevel.Trace:
                Logger.Trace(logString);
                break;
            case PacketLogLevel.Debug:
                Logger.Debug(logString);
                break;
            case PacketLogLevel.Info:
                Logger.Info(logString);
                break;
            case PacketLogLevel.Warning:
                Logger.Warn(logString);
                break;
            case PacketLogLevel.Error:
                Logger.Error(logString);
                break;
            case PacketLogLevel.Fatal:
                Logger.Fatal(logString);
                break;
            case PacketLogLevel.Off:
            default:
                break;
        }

        return ps;
    }

    public override PacketBase<GameConnection> Decode(PacketStream ps)
    {
        try
        {
            Read(ps);

            var logString = $"GamePacket: C->S type {TypeId:X3} {ToString()?.Substring(23)}{Verbose()}";
            switch (LogLevel)
            {
                case PacketLogLevel.Trace:
                    Logger.Trace(logString);
                    break;
                case PacketLogLevel.Debug:
                    Logger.Debug(logString);
                    break;
                case PacketLogLevel.Info:
                    Logger.Info(logString);
                    break;
                case PacketLogLevel.Warning:
                    Logger.Warn(logString);
                    break;
                case PacketLogLevel.Error:
                    Logger.Error(logString);
                    break;
                case PacketLogLevel.Fatal:
                    Logger.Fatal(logString);
                    break;
                case PacketLogLevel.Off:
                default:
                    break;
            }

            Execute();
        }
        catch (Exception ex)
        {
            Logger.Error("GamePacket: C->S type {0:X3} {1}", TypeId, ToString()?.Substring(23));
            Logger.Fatal(ex);
            throw;
        }

        return this;
    }
}
