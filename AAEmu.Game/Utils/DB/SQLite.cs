using System;
using System.IO;
using AAEmu.Commons.IO;
using Microsoft.Data.Sqlite;
using NLog;

namespace AAEmu.Game.Utils.DB
{
    public static class SQLite
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();
        private static readonly object DatabasePathLock = new object();
        private static string _configuredReadOnlyDatabasePath;

        public static string DatabasePath
        {
            get
            {
                lock (DatabasePathLock)
                    return _configuredReadOnlyDatabasePath ??
                           Path.Combine(FileManager.AppPath, "Data", "compact.sqlite3");
            }
        }

        public static void ConfigureReadOnlyDatabasePath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("A compact SQLite path is required", nameof(path));

            var fullPath = Path.GetFullPath(path);
            if (!File.Exists(fullPath))
                throw new FileNotFoundException("Compact SQLite database does not exist", fullPath);

            lock (DatabasePathLock)
                _configuredReadOnlyDatabasePath = fullPath;
        }

        public static IDisposable PushReadOnlyDatabasePath(string path)
        {
            string previous;
            lock (DatabasePathLock)
                previous = _configuredReadOnlyDatabasePath;
            ConfigureReadOnlyDatabasePath(path);
            return new DatabasePathScope(previous);
        }

        public static SqliteConnection CreateConnection()
        {
            var dbPath = DatabasePath;
            if (!File.Exists(dbPath))
            {
                _log.Fatal("Server database does not exist: {0} !",dbPath);
                return null;
            }
            var connection = new SqliteConnection($"Data Source=file:{dbPath}; Mode=ReadOnly");
            try
            {
                connection.Open();
            }
            catch (Exception e)
            {
                _log.Error(e,"Error on SQLite connect: {0}", e.Message);
                return null;
            }

            return connection;
        }

        private sealed class DatabasePathScope : IDisposable
        {
            private string _previous;
            private bool _disposed;

            public DatabasePathScope(string previous)
            {
                _previous = previous;
            }

            public void Dispose()
            {
                if (_disposed)
                    return;
                lock (DatabasePathLock)
                    _configuredReadOnlyDatabasePath = _previous;
                _disposed = true;
            }
        }
    }
}
