using System;
using System.IO;
using System.Linq;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Merchant;
using Newtonsoft.Json;
using Xunit;

namespace AAEmu.Tests
{
    public class MerchantPurchaseCaptureServiceTests
    {
        [Fact]
        public void RejectedBatchesPersistEachMerchantItemRelationOnlyOnce()
        {
            var directory = Path.Combine(
                Path.GetTempPath(),
                "aaemu-merchant-capture-" + Guid.NewGuid().ToString("N"));
            var path = Path.Combine(directory, "captures.jsonl");

            try
            {
                var service = CreateService(path);
                var firstBatch = CreateBatch(
                    new MerchantPurchaseRequest
                    {
                        ItemId = 47868,
                        Grade = 0,
                        Count = 1,
                        Currency = ShopCurrencyType.Money
                    },
                    new MerchantPurchaseRequest
                    {
                        ItemId = 47868,
                        Grade = 0,
                        Count = 5,
                        Currency = ShopCurrencyType.Money
                    },
                    new MerchantPurchaseRequest
                    {
                        ItemId = 47869,
                        Grade = 2,
                        Count = 3,
                        Currency = ShopCurrencyType.Honor
                    });

                Assert.Equal(2, service.CaptureRejectedBatch(firstBatch));
                Assert.Equal(0, service.CaptureRejectedBatch(firstBatch));

                // A new process must rebuild the same deduplication set from
                // the persisted JSONL before accepting another observation.
                var restarted = CreateService(path);
                Assert.Equal(0, restarted.CaptureRejectedBatch(firstBatch));
                Assert.Equal(
                    1,
                    restarted.CaptureRejectedBatch(
                        CreateBatch(
                            new MerchantPurchaseRequest
                            {
                                ItemId = 50000,
                                Grade = 0,
                                Count = 1,
                                Currency = ShopCurrencyType.VocationBadges
                            })));

                var records = File.ReadAllLines(path)
                    .Select(JsonConvert.DeserializeObject<MerchantPurchaseCaptureRecord>)
                    .ToArray();
                Assert.Equal(3, records.Length);
                Assert.All(
                    records,
                    record => Assert.Equal(
                        MerchantPurchaseCaptureService.CaptureSchema,
                        record.Schema));
                Assert.Equal(3, records.Select(record => record.DeduplicationKey).Distinct().Count());
                Assert.Equal((uint)5342, records[0].Merchant.NpcTemplateId);
                Assert.Equal((uint)914119, records[0].Merchant.MerchantPackId);
                Assert.Equal("prepare", records[0].FailureStage);
                Assert.False(records[0].ServerEvidence.ExactStockRelationPresent);
            }
            finally
            {
                if (Directory.Exists(directory))
                    Directory.Delete(directory, true);
            }
        }

        [Fact]
        public void DisabledCaptureNeverCreatesAFile()
        {
            var path = Path.Combine(
                Path.GetTempPath(),
                "aaemu-disabled-merchant-capture-" + Guid.NewGuid().ToString("N"),
                "captures.jsonl");
            var service = new MerchantPurchaseCaptureService(false, path);

            Assert.Equal(0, service.CaptureRejectedBatch(CreateBatch(
                new MerchantPurchaseRequest
                {
                    ItemId = 47868,
                    Grade = 0,
                    Count = 1,
                    Currency = ShopCurrencyType.Money
                })));
            Assert.False(File.Exists(path));
        }

        [Fact]
        public void FailedWriteDoesNotSuppressTheNextObservation()
        {
            var directory = Path.Combine(
                Path.GetTempPath(),
                "aaemu-merchant-retry-" + Guid.NewGuid().ToString("N"));
            var path = Path.Combine(directory, "captures.jsonl");
            var batch = CreateBatch(
                new MerchantPurchaseRequest
                {
                    ItemId = 47868,
                    Grade = 0,
                    Count = 1,
                    Currency = ShopCurrencyType.Money
                });

            try
            {
                Directory.CreateDirectory(path);
                var service = CreateService(path);
                Assert.Equal(0, service.CaptureRejectedBatch(batch));

                Directory.Delete(path);
                Assert.Equal(1, service.CaptureRejectedBatch(batch));
                Assert.Single(File.ReadAllLines(path));
            }
            finally
            {
                if (Directory.Exists(directory))
                    Directory.Delete(directory, true);
            }
        }

        private static MerchantPurchaseCaptureService CreateService(string path)
        {
            return new MerchantPurchaseCaptureService(
                true,
                path,
                (batch, request) => new MerchantPurchaseCaptureServerEvidence
                {
                    MerchantPackLoaded = true,
                    ExactStockRelationPresent = false,
                    NativeCoverageCatalogueAvailable = true,
                    CoverageState = "Unknown",
                    CoverageCanCreate = false
                });
        }

        private static MerchantPurchaseCaptureBatch CreateBatch(
            params MerchantPurchaseRequest[] requests)
        {
            return new MerchantPurchaseCaptureBatch
            {
                FailureStage = "prepare",
                FailureReason = "item is not in the authoritative stock",
                CharacterId = 42,
                CharacterName = "CaptureTester",
                NpcObjId = 37049,
                NpcTemplateId = 5342,
                NpcName = "Deven",
                NpcMerchantFlag = true,
                MerchantPackId = 914119,
                Requests = requests
            };
        }
    }
}
