using Microsoft.Data.Sqlite;

namespace AAEmu.Game.Utils.DB;

public sealed class SQLiteWrapperReader(SqliteDataReader reader) : IDisposable
{
    private readonly Dictionary<string, int> _ordinal = [];

    public bool Read() => reader.Read();

    public object GetValue(string column)
    {
        return reader.GetValue(GetOrdinal(column));
    }

    public bool GetBoolean(string column)
    {
        var ordinal = GetOrdinal(column);
        if (reader.IsDBNull(ordinal))
            return false;

        var value = reader.GetValue(ordinal);
        return value switch
        {
            bool boolean => boolean,
            byte or sbyte or short or ushort or int or uint or long or ulong => Convert.ToInt64(value) != 0,
            string text => text is "t" or "1" || text.Equals("true", StringComparison.OrdinalIgnoreCase),
            _ => reader.GetBoolean(ordinal)
        };
    }

    public bool GetBoolean(string column, bool fromString)
    {
        if (fromString)
        {
            if (IsDBNull(column))
                return false;

            var value = GetString(column);
            return value is "t" or "1" || value.Equals("true", StringComparison.OrdinalIgnoreCase);
        }

        return GetBoolean(column);
    }

    public bool GetBooleanOrDefault(string column, bool defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal) || reader.IsDBNull(ordinal))
            return defaultValue;

        var value = reader.GetValue(ordinal);
        return value switch
        {
            bool boolean => boolean,
            byte or sbyte or short or ushort or int or uint or long or ulong => Convert.ToInt64(value) != 0,
            string text => text is "t" or "1" || text.Equals("true", StringComparison.OrdinalIgnoreCase),
            _ => Convert.ToBoolean(value)
        };
    }

    public byte GetByte(string column)
    {
        return reader.GetByte(GetOrdinal(column));
    }

    public byte GetByte(string column, byte defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal))
            return defaultValue;
        if (reader.IsDBNull(ordinal))
            return defaultValue;
        return reader.GetByte(ordinal);
    }

    public long GetBytes(string column, long fieldOffset, byte[] buffer, int bufferOffset, int length)
    {
        return reader.GetBytes(GetOrdinal(column), fieldOffset, buffer, bufferOffset, length);
    }

    public char GetChar(string column)
    {
        return reader.GetChar(GetOrdinal(column));
    }

    public long GetChars(string column, long fieldOffset, char[] buffer, int bufferOffset, int length)
    {
        return reader.GetChars(GetOrdinal(column), fieldOffset, buffer, bufferOffset, length);
    }

    public Guid GetGuid(string column)
    {
        return reader.GetGuid(GetOrdinal(column));
    }

    public short GetInt16(string column)
    {
        return reader.GetInt16(GetOrdinal(column));
    }

    public ushort GetUInt16(string column) => (ushort)GetInt16(column);

    public int GetInt32(string column)
    {
        //Same impl of Sqlite.Core v2.2.1
        return (int)reader.GetInt64(GetOrdinal(column));
    }

    public int GetInt32(string column, int defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal))
            return defaultValue;
        if (reader.IsDBNull(ordinal))
            return defaultValue;

        //Same impl of Sqlite.Core v2.2.1
        return (int)reader.GetInt64(ordinal);
    }

    public uint GetUInt32(string column) => (uint)GetInt32(column);

    public uint GetUInt32(string column, uint defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal))
            return defaultValue;
        if (reader.IsDBNull(ordinal))
            return defaultValue;
        return (uint)GetInt32(column);
    }

    public long GetInt64(string column)
    {
        return reader.GetInt64(GetOrdinal(column));
    }

    public long GetInt64(string column, long defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal) || reader.IsDBNull(ordinal))
            return defaultValue;
        return reader.GetInt64(ordinal);
    }

    public ulong GetUInt64(string column) => (ulong)GetInt64(column);

    public float GetFloat(string column)
    {
        return reader.GetFloat(GetOrdinal(column));
    }

    public float GetFloat(string column, float defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal))
            return defaultValue;
        if (reader.IsDBNull(ordinal))
            return defaultValue;
        return reader.GetFloat(ordinal);
    }

    public double GetDouble(string column)
    {
        return reader.GetDouble(GetOrdinal(column));
    }

    public string GetString(string column)
    {
        return reader.GetString(GetOrdinal(column));
    }

    public string GetString(string column, string defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal))
            return defaultValue;
        if (reader.IsDBNull(ordinal))
            return defaultValue;
        return reader.GetString(ordinal);
    }

    public decimal GetDecimal(string column)
    {
        return reader.GetDecimal(GetOrdinal(column));
    }

    public DateTime GetDateTime(string column)
    {
        return reader.GetDateTime(GetOrdinal(column));
    }

    public DateTime GetDateTimeOrUnixSeconds(string column, DateTime defaultValue)
    {
        if (!TryGetOrdinal(column, out var ordinal) || reader.IsDBNull(ordinal))
            return defaultValue;

        var value = reader.GetValue(ordinal);
        if (value is long unixSeconds)
            return unixSeconds == 0 ? defaultValue : DateTimeOffset.FromUnixTimeSeconds(unixSeconds).UtcDateTime;

        if (value is string text)
        {
            if (long.TryParse(text, out unixSeconds))
                return unixSeconds == 0 ? defaultValue : DateTimeOffset.FromUnixTimeSeconds(unixSeconds).UtcDateTime;
            if (DateTime.TryParse(text, System.Globalization.CultureInfo.InvariantCulture,
                    System.Globalization.DateTimeStyles.AssumeUniversal |
                    System.Globalization.DateTimeStyles.AdjustToUniversal, out var parsed))
                return parsed;
        }

        return reader.GetDateTime(ordinal);
    }

    public bool IsDBNull(string column)
    {
        return reader.IsDBNull(GetOrdinal(column));
    }

    public int GetOrdinal(string column)
    {
        if (_ordinal.TryGetValue(column, out var ordinal1))
            return ordinal1;

        var ordinal = reader.GetOrdinal(column);
        _ordinal.Add(column, ordinal);
        return ordinal;
    }

    public bool TryGetOrdinal(string column, out int ordinal)
    {
        if (_ordinal.TryGetValue(column, out ordinal))
            return ordinal >= 0;

        for (var index = 0; index < reader.FieldCount; index++)
        {
            if (!string.Equals(reader.GetName(index), column, StringComparison.OrdinalIgnoreCase))
                continue;
            _ordinal[column] = index;
            ordinal = index;
            return true;
        }

        _ordinal[column] = -1;
        ordinal = -1;
        return false;
    }

    public void Dispose()
    {
        _ordinal.Clear();
        reader.Dispose();
    }

    public List<string> GetColumnNames()
    {
        var res = new List<string>();
        for (var i = 0; i < reader.FieldCount; i++)
            res.Add(reader.GetName(i));
        return res;
    }
}
