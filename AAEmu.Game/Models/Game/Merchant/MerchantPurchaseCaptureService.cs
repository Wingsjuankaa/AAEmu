using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

using AAEmu.Commons.IO;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using Newtonsoft.Json;
using NLog;

namespace AAEmu.Game.Models.Game.Merchant
{
    public sealed class MerchantPurchaseCaptureBatch
    {
        public string FailureStage { get; set; }
        public string FailureReason { get; set; }
        public uint CharacterId { get; set; }
        public string CharacterName { get; set; }
        public uint NpcObjId { get; set; }
        public uint NpcTemplateId { get; set; }
        public string NpcName { get; set; }
        public bool NpcMerchantFlag { get; set; }
        public uint MerchantPackId { get; set; }
        public uint DoodadObjId { get; set; }
        public uint DoodadTemplateId { get; set; }
        public uint UnknownId { get; set; }
        public bool UseAaPoint { get; set; }
        public byte OpenType { get; set; }
        public MerchantGoods Stock { get; set; }
        public IReadOnlyList<MerchantPurchaseRequest> Requests { get; set; }
    }

    public sealed class MerchantPurchaseCaptureRecord
    {
        public string Schema { get; set; }
        public DateTime CapturedAtUtc { get; set; }
        public string BatchId { get; set; }
        public string DeduplicationKey { get; set; }
        public string FailureStage { get; set; }
        public string FailureReason { get; set; }
        public MerchantPurchaseCaptureCharacter Character { get; set; }
        public MerchantPurchaseCaptureActor Merchant { get; set; }
        public MerchantPurchaseCaptureItem Item { get; set; }
        public MerchantPurchaseCaptureServerEvidence ServerEvidence { get; set; }
    }

    public sealed class MerchantPurchaseCaptureCharacter
    {
        public uint Id { get; set; }
        public string Name { get; set; }
    }

    public sealed class MerchantPurchaseCaptureActor
    {
        public string ActorKind { get; set; }
        public uint NpcObjId { get; set; }
        public uint NpcTemplateId { get; set; }
        public string NpcName { get; set; }
        public bool NpcMerchantFlag { get; set; }
        public uint MerchantPackId { get; set; }
        public uint DoodadObjId { get; set; }
        public uint DoodadTemplateId { get; set; }
        public uint UnknownId { get; set; }
        public bool UseAaPoint { get; set; }
        public byte OpenType { get; set; }
    }

    public sealed class MerchantPurchaseCaptureItem
    {
        public uint ItemId { get; set; }
        public byte Grade { get; set; }
        public int Count { get; set; }
        public byte CurrencyId { get; set; }
        public string Currency { get; set; }
    }

    public sealed class MerchantPurchaseCaptureServerEvidence
    {
        public bool MerchantPackLoaded { get; set; }
        public bool ExactStockRelationPresent { get; set; }
        public int? StockPrice { get; set; }
        public bool ItemTemplateLoaded { get; set; }
        public string ItemTemplateName { get; set; }
        public int? ItemTemplateMoneyPrice { get; set; }
        public int? ItemTemplateHonorPrice { get; set; }
        public int? ItemTemplateVocationPrice { get; set; }
        public bool NativeCoverageCatalogueAvailable { get; set; }
        public string CoverageState { get; set; }
        public bool CoverageCanCreate { get; set; }
        public string ConcreteType { get; set; }
        public string MissingDependencies { get; set; }
        public string Provenance { get; set; }
    }

    /// <summary>
    /// Persists the first failed observation of each merchant/item relation as
    /// JSON Lines. The append-only format preserves completed records if the
    /// process stops while a later record is being written.
    /// </summary>
    public sealed class MerchantPurchaseCaptureService
    {
        public const string CaptureSchema =
            "AA8_MERCHANT_PURCHASE_RECONSTRUCTION_CAPTURE_V1";
        public const string EnabledEnvironmentVariable =
            "AAEMU_MERCHANT_PURCHASE_CAPTURE_ENABLED";
        public const string PathEnvironmentVariable =
            "AAEMU_MERCHANT_PURCHASE_CAPTURE_PATH";

        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly object _sync = new object();
        private readonly bool _enabled;
        private readonly string _path;
        private readonly Func<
            MerchantPurchaseCaptureBatch,
            MerchantPurchaseRequest,
            MerchantPurchaseCaptureServerEvidence> _evidenceFactory;
        private HashSet<string> _knownRelations;

        public static MerchantPurchaseCaptureService Instance { get; } =
            CreateFromEnvironment();

        public MerchantPurchaseCaptureService(
            bool enabled,
            string path,
            Func<
                MerchantPurchaseCaptureBatch,
                MerchantPurchaseRequest,
                MerchantPurchaseCaptureServerEvidence> evidenceFactory = null)
        {
            _enabled = enabled;
            _path = path;
            _evidenceFactory = evidenceFactory ?? BuildServerEvidence;
        }

        public string Path => _path;

        public int CaptureRejectedBatch(MerchantPurchaseCaptureBatch batch)
        {
            if (!_enabled || batch?.Requests == null || batch.Requests.Count == 0)
                return 0;

            try
            {
                lock (_sync)
                {
                    EnsureInitialized();
                    var batchId = Guid.NewGuid().ToString("N");
                    var capturedAtUtc = DateTime.UtcNow;
                    var records = new List<MerchantPurchaseCaptureRecord>();
                    var pendingKeys = new HashSet<string>(StringComparer.Ordinal);

                    foreach (var request in batch.Requests.Where(request => request != null))
                    {
                        var key = BuildDeduplicationKey(batch, request);
                        if (_knownRelations.Contains(key) || !pendingKeys.Add(key))
                            continue;
                        records.Add(BuildRecord(batch, request, key, batchId, capturedAtUtc));
                    }

                    if (records.Count == 0)
                        return 0;

                    var directory = System.IO.Path.GetDirectoryName(_path);
                    if (!string.IsNullOrWhiteSpace(directory))
                        Directory.CreateDirectory(directory);

                    using (var stream = new FileStream(
                               _path,
                               FileMode.Append,
                               FileAccess.Write,
                               FileShare.Read))
                    using (var writer = new StreamWriter(
                               stream,
                               new UTF8Encoding(false)))
                    {
                        foreach (var record in records)
                        {
                            writer.WriteLine(
                                JsonConvert.SerializeObject(
                                    record,
                                    Formatting.None));
                        }
                        writer.Flush();
                        stream.Flush(true);
                    }

                    foreach (var key in pendingKeys)
                        _knownRelations.Add(key);

                    Log.Warn(
                        "AA8 merchant reconstruction captured {0} new relation(s) " +
                        "in {1} after {2}: {3}",
                        records.Count,
                        _path,
                        batch.FailureStage,
                        batch.FailureReason);
                    return records.Count;
                }
            }
            catch (Exception exception)
            {
                // Observation must never become part of the purchase outcome.
                Log.Error(
                    exception,
                    "Failed to persist AA8 merchant reconstruction capture to {0}",
                    _path);
                return 0;
            }
        }

        public static string BuildDeduplicationKey(
            MerchantPurchaseCaptureBatch batch,
            MerchantPurchaseRequest request)
        {
            var actorKind = batch.NpcTemplateId != 0 ? "npc" : "doodad";
            return string.Join(
                "|",
                actorKind,
                batch.NpcTemplateId,
                batch.MerchantPackId,
                batch.DoodadTemplateId,
                request.ItemId,
                request.Grade,
                (byte)request.Currency);
        }

        private static MerchantPurchaseCaptureService CreateFromEnvironment()
        {
            var enabled = string.Equals(
                Environment.GetEnvironmentVariable(EnabledEnvironmentVariable),
                "1",
                StringComparison.Ordinal);
            var path = Environment.GetEnvironmentVariable(PathEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(path))
            {
                path = System.IO.Path.Combine(
                    FileManager.AppPath,
                    "runtime-captures",
                    "merchant-purchase-reconstruction.jsonl");
            }
            return new MerchantPurchaseCaptureService(enabled, path);
        }

        private void EnsureInitialized()
        {
            if (_knownRelations != null)
                return;
            _knownRelations = new HashSet<string>(StringComparer.Ordinal);
            if (!File.Exists(_path))
                return;

            foreach (var line in File.ReadLines(_path))
            {
                if (string.IsNullOrWhiteSpace(line))
                    continue;
                try
                {
                    var record = JsonConvert.DeserializeObject<MerchantPurchaseCaptureRecord>(line);
                    if (!string.IsNullOrWhiteSpace(record?.DeduplicationKey))
                        _knownRelations.Add(record.DeduplicationKey);
                }
                catch (JsonException)
                {
                    // A torn final append is recoverable: keep every valid
                    // relation and allow the damaged relation to be observed again.
                    Log.Warn(
                        "Ignoring malformed line in AA8 merchant capture {0}",
                        _path);
                }
            }
        }

        private MerchantPurchaseCaptureRecord BuildRecord(
            MerchantPurchaseCaptureBatch batch,
            MerchantPurchaseRequest request,
            string key,
            string batchId,
            DateTime capturedAtUtc)
        {
            return new MerchantPurchaseCaptureRecord
            {
                Schema = CaptureSchema,
                CapturedAtUtc = capturedAtUtc,
                BatchId = batchId,
                DeduplicationKey = key,
                FailureStage = batch.FailureStage,
                FailureReason = batch.FailureReason,
                Character = new MerchantPurchaseCaptureCharacter
                {
                    Id = batch.CharacterId,
                    Name = batch.CharacterName
                },
                Merchant = new MerchantPurchaseCaptureActor
                {
                    ActorKind = batch.NpcTemplateId != 0
                        ? "npc"
                        : batch.DoodadObjId != 0 || batch.DoodadTemplateId != 0
                            ? "doodad"
                            : "global",
                    NpcObjId = batch.NpcObjId,
                    NpcTemplateId = batch.NpcTemplateId,
                    NpcName = batch.NpcName,
                    NpcMerchantFlag = batch.NpcMerchantFlag,
                    MerchantPackId = batch.MerchantPackId,
                    DoodadObjId = batch.DoodadObjId,
                    DoodadTemplateId = batch.DoodadTemplateId,
                    UnknownId = batch.UnknownId,
                    UseAaPoint = batch.UseAaPoint,
                    OpenType = batch.OpenType
                },
                Item = new MerchantPurchaseCaptureItem
                {
                    ItemId = request.ItemId,
                    Grade = request.Grade,
                    Count = request.Count,
                    CurrencyId = (byte)request.Currency,
                    Currency = request.Currency.ToString()
                },
                ServerEvidence = _evidenceFactory(batch, request)
            };
        }

        private static MerchantPurchaseCaptureServerEvidence BuildServerEvidence(
            MerchantPurchaseCaptureBatch batch,
            MerchantPurchaseRequest request)
        {
            var stockItem = batch.Stock?.GetStock(
                request.ItemId,
                request.Grade,
                request.Currency);
            var template = Core.Managers.ItemManager.Instance.GetTemplate(request.ItemId);
            var coverageService = ItemDefinitionCoverageService.Instance;
            var coverage = coverageService.Get(request.ItemId);

            return new MerchantPurchaseCaptureServerEvidence
            {
                MerchantPackLoaded = batch.Stock != null,
                ExactStockRelationPresent = stockItem != null,
                StockPrice = stockItem?.Price,
                ItemTemplateLoaded = template != null,
                ItemTemplateName = template?.Name,
                ItemTemplateMoneyPrice = template?.Price,
                ItemTemplateHonorPrice = template?.HonorPrice,
                ItemTemplateVocationPrice = template?.LivingPointPrice,
                NativeCoverageCatalogueAvailable =
                    coverageService.NativeCatalogueAvailable,
                CoverageState = coverage.State.ToString(),
                CoverageCanCreate = coverage.CanCreate,
                ConcreteType = coverage.ConcreteType,
                MissingDependencies = coverage.MissingDependencies,
                Provenance = coverage.Provenance
            };
        }
    }
}
