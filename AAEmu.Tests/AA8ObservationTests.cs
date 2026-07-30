using System;
using System.IO;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Observations;
using Microsoft.Data.Sqlite;
using Xunit;

namespace AAEmu.Tests
{
    public class AA8ObservationTests
    {
        [Fact]
        public void GateAllowsExactlyOneInteractionUntilContinue()
        {
            var gate = new AA8ObservationGate();

            Assert.True(gate.TryBegin("first"));
            Assert.False(gate.TryBegin("second"));
            gate.Complete("first");
            Assert.False(gate.TryBegin("second"));
            Assert.Equal("first", gate.LastInteractionId);
            Assert.True(gate.Continue());
            Assert.True(gate.TryBegin("second"));
        }

        [Fact]
        public void StoreCreatesSchemaAndFlushesQueuedWrites()
        {
            var path = Path.Combine(
                Path.GetTempPath(),
                $"aa8-observation-{Guid.NewGuid():N}.sqlite3");
            try
            {
                using (var store = new AA8ObservationStore(path, 32, 8, 25))
                {
                    store.Start();
                    Assert.True(
                        store.TryEnqueue(
                            @"INSERT OR REPLACE INTO schema_info(
schema_name,schema_version,authority_boundary)
VALUES($name,$version,$boundary)",
                            ("$name", "TEST"),
                            ("$version", 1),
                            ("$boundary", "observed_runtime_only_not_native_authority")));
                    Assert.True(store.Flush(TimeSpan.FromSeconds(5)));
                }

                using (var connection = new SqliteConnection($"Data Source={path}"))
                {
                    connection.Open();
                    using (var command = connection.CreateCommand())
                    {
                        command.CommandText =
                            "SELECT authority_boundary FROM schema_info WHERE schema_name='TEST'";
                        Assert.Equal(
                            "observed_runtime_only_not_native_authority",
                            command.ExecuteScalar());
                    }
                }
            }
            finally
            {
                DeleteIfPresent(path);
                DeleteIfPresent(path + "-wal");
                DeleteIfPresent(path + "-shm");
            }
        }

        private static void DeleteIfPresent(string path)
        {
            if (File.Exists(path))
                File.Delete(path);
        }
    }
}
