namespace AAEmu.Game.Models.Game.Housing;

public sealed class HousingInteractionCatalogFile
{
    public int SchemaVersion { get; set; }
    public string ClientBuild { get; set; }
    public string FullSha256 { get; set; }
    public string CompactSha256 { get; set; }
    public string X2GameSha256 { get; set; }
    public List<HousingBindingDefinition> Bindings { get; set; } = [];
}

public sealed class HousingInteractionCatalog
{
    public const int CurrentSchemaVersion = 1;

    private readonly Dictionary<uint, IReadOnlyList<HousingBindingDefinition>> _byHousing;
    private readonly Dictionary<(uint HousingTemplateId, byte AttachPointId, uint DoodadId), HousingBindingDefinition>
        _byIdentity;

    public static HousingInteractionCatalog Empty { get; } = new([]);

    public int BindingCount => _byIdentity.Count;
    public int HousingTemplateCount => _byHousing.Count;

    private HousingInteractionCatalog(IEnumerable<HousingBindingDefinition> definitions)
    {
        _byIdentity = [];
        var grouped = new Dictionary<uint, List<HousingBindingDefinition>>();

        foreach (var definition in definitions
                     .OrderBy(x => x.HousingTemplateId)
                     .ThenBy(x => (byte)x.AttachPointId)
                     .ThenBy(x => x.DoodadId))
        {
            var key = (definition.HousingTemplateId, (byte)definition.AttachPointId, definition.DoodadId);
            if (!_byIdentity.TryAdd(key, definition))
                throw new InvalidDataException(
                    $"Duplicate AA10 housing binding {definition.HousingTemplateId}/{definition.AttachPointId}/{definition.DoodadId}");

            if (!grouped.TryGetValue(definition.HousingTemplateId, out var list))
                grouped[definition.HousingTemplateId] = list = [];
            list.Add(definition);
        }

        _byHousing = grouped.ToDictionary(
            pair => pair.Key,
            pair => (IReadOnlyList<HousingBindingDefinition>)pair.Value.AsReadOnly());
    }

    public static HousingInteractionCatalog Create(IEnumerable<HousingBindingDefinition> definitions) =>
        new(definitions ?? []);

    public bool TryGetBindings(uint housingTemplateId, out IReadOnlyList<HousingBindingDefinition> bindings)
    {
        if (_byHousing.TryGetValue(housingTemplateId, out bindings))
            return true;
        bindings = [];
        return false;
    }

    public bool TryGetDefinition(
        uint housingTemplateId,
        byte attachPointId,
        uint doodadId,
        out HousingBindingDefinition definition) =>
        _byIdentity.TryGetValue((housingTemplateId, attachPointId, doodadId), out definition);
}
