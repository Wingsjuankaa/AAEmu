using AAEmu.Commons.Exceptions;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Units;

using NLog;

namespace AAEmu.Game.Models.Game.Items.Containers;

public class ItemContainer
{
    protected static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    private int _containerSize;
    private int _freeSlotCount;
    private ICharacter _owner;
    private uint _ownerId;
    public bool IsDirty { get; set; }
    private readonly SlotType _containerType;
    private ulong _containerId;

    public Unit ParentUnit { get; set; }

    public ICharacter Owner
    {
        get
        {
            if (_owner == null && _ownerId > 0)
            {
                _owner = WorldManager.Instance.GetCharacterById(_ownerId);
            }

            return _owner;
        }
        set
        {
            _owner = value;
            if (value?.Id != _ownerId)
            {
                _ownerId = value?.Id ?? 0;
                IsDirty = true;
            }
        }
    }

    public uint OwnerId
    {
        get => _owner?.Id ?? _ownerId;
        protected set
        {
            if (value != _ownerId)
            {
                _ownerId = value;
                IsDirty = true;
            }

            _owner = null; // this will make it so that it will try to fetch on the next query
        }
    }

    public uint MateId { get; set; }

    public SlotType ContainerType
    {
        get => _containerType;
        private init
        {
            if (value != _containerType)
            {
                _containerType = value;
                IsDirty = true;
            }
        }
    }

    public ulong ContainerId
    {
        get => _containerId;
        set
        {
            if (value != _containerId)
            {
                _containerId = value;
                IsDirty = true;
            }
        }
    }

    public List<Item> Items { get; set; }

    private bool PartOfPlayerInventory =>
        ContainerType switch
        {
            SlotType.None => false,
            SlotType.Equipment => true,
            SlotType.Inventory => true,
            SlotType.Bank => true,
            SlotType.Trade => true,
            SlotType.Mail => false,
            SlotType.System => false,
            SlotType.EquipmentMate => false,
            SlotType.EquipmentSlave => false,
            SlotType.Auction => false,
            _ => throw new ArgumentOutOfRangeException()
        };

    public int ContainerSize
    {
        get => _containerSize;
        set
        {
            if (value != _containerSize)
            {
                _containerSize = value;
                IsDirty = true;
            }

            UpdateFreeSlotCount();
        }
    }

    public int FreeSlotCount => _freeSlotCount;

    protected ItemContainer()
    {
        // Only relevant for inheritance
        Owner = null;
        ContainerType = SlotType.None;
        Items = [];
        ContainerSize = 0;
    }

    /// <summary>
    /// Creates a Container
    /// </summary>
    /// <param name="ownerId">Player Id for this container</param>
    /// <param name="containerType"></param>
    /// <param name="createWithNewId"></param>
    /// <param name="parentUnit">Parent that will actually hold this container (can be different from Owner)</param>
    public ItemContainer(uint ownerId, SlotType containerType, bool createWithNewId, Unit parentUnit)
    {
        OwnerId = ownerId;
        ContainerType = containerType;
        ParentUnit = parentUnit;
        Items = [];
        ContainerSize = -1; // Unlimited
        if (createWithNewId)
        {
            ContainerId = ContainerIdManager.Instance.GetNextId();
        }
    }

    public void ReNumberSlots(bool reverse = false)
    {
        for (var c = 0; c < Items.Count; c++)
        {
            var i = Items[reverse ? Items.Count - 1 - c : c];
            i.SlotType = ContainerType;
            i.Slot = c;
        }
    }

    public void UpdateFreeSlotCount()
    {
        if (_containerSize < 0)
        {
            _freeSlotCount = 9999; // Should be more than enough
            return;
        }

        var usedSlotsCount = Items.Count(i => i != null);
        _freeSlotCount = _containerSize - usedSlotsCount;
    }

    /// <summary>
    /// Returns a slot index number of the first free location in an inventory
    /// </summary>
    /// <param name="preferredSlot">Preferred location if available</param>
    /// <returns>Location if an empty slot was found, or -1 in case the item container is full</returns>
    public int GetUnusedSlot(int preferredSlot)
    {
        // No max size defined, get the highest number and add one
        if (_containerSize < 0)
        {
            var highestSlot = -1;
            foreach (var i in Items)
            {
                if (i.Slot > highestSlot)
                {
                    highestSlot = i.Slot;
                }
            }

            highestSlot++;
            return preferredSlot > highestSlot ? preferredSlot : highestSlot;
        }

        // Check the preferred slot to see if it's free, or if we need to assign a new one
        var needNewSlot = false;
        if (preferredSlot < 0)
        {
            needNewSlot = true;
        }
        else
        {
            foreach (var i in Items)
            {
                if (i.Slot == preferredSlot)
                {
                    needNewSlot = true;
                    break;
                }
            }
        }

        // Find a new slot if needed
        if (needNewSlot)
        {
            var usedSlots = (from iSlot in Items where iSlot.Slot != preferredSlot select iSlot.Slot).ToList();
            for (var i = 0; i < ContainerSize; i++)
            {
                if (!usedSlots.Contains(i))
                {
                    return i;
                }
            }

            // inventory container is full
            return -1;
        }
        // Otherwise just return the preferred slot
        else
        {
            return preferredSlot;
        }
    }

    private bool TryGetItemBySlot(int slot, out Item theItem)
    {
        foreach (var i in Items)
        {
            if (i.Slot == slot)
            {
                theItem = i;
                return true;
            }
        }

        theItem = null;
        return false;
    }

    public Item GetItemBySlot(int slot)
    {
        if (TryGetItemBySlot(slot, out var res))
        {
            return res;
        }
        else
        {
            return null;
        }
    }

    private bool TryGetItemByItemId(ulong itemId, out Item theItem)
    {
        foreach (var i in Items)
        {
            if (i.Id == itemId)
            {
                theItem = i;
                return true;
            }
        }

        theItem = null;
        return false;
    }

    public Item GetItemByItemId(ulong itemId)
    {
        if (TryGetItemByItemId(itemId, out var res))
        {
            return res;
        }
        else
        {
            return null;
        }
    }

    /// <summary>
    /// Adds an Item Object to this container and also updates source container, for new items like craft results, use AcquireDefaultItem instead
    /// </summary>
    /// <param name="taskType"></param>
    /// <param name="item">Item Object to add/move to this container</param>
    /// <param name="preferredSlot">preferred slot to place this item in</param>
    /// <returns>Fails on Full Inventory or if target slot is invalid</returns>
    public bool AddOrMoveExistingItem(ItemTaskType taskType, Item item, int preferredSlot = -1)
    {
        if (item == null)
        {
            return false;
        }

        var sourceContainer = item._holdingContainer;
        var sourceSlot = (byte)item.Slot;
        var sourceSlotType = item.SlotType;

        var currentPreferredSlotItem = GetItemBySlot(preferredSlot);
        var newSlot = -1;
        var canAddToSameSlot = false;

        // When adding wearables to equipment container, for the slot numbers if needed
        if (this is EquipmentContainer && item is EquipItem _ && preferredSlot < 0)
        {
            var validSlots = EquipmentContainer.GetAllowedGearSlots(item.Template);
            // find valid empty slot (if any), stop looking if it is the preferred slot
            foreach (var vSlot in validSlots)
            {
                if (GetItemBySlot((int)vSlot) == null)
                {
                    newSlot = (int)vSlot;
                    break;
                }
            }
        }

        // Make sure the item is in container size's range
        if (
            ContainerType == SlotType.Inventory && item.Template.MaxCount > 1 &&
            currentPreferredSlotItem != null &&
            currentPreferredSlotItem.TemplateId == item.TemplateId && currentPreferredSlotItem.Grade == item.Grade &&
            item.Count + currentPreferredSlotItem.Count <= item.Template.MaxCount)
        {
            newSlot = preferredSlot;
            canAddToSameSlot = true;
        }
        else
        {
            if (newSlot < 0)
            {
                // Equipment slots are fixed by slot type: an explicit target slot IS the destination, so use it
                // directly instead of GetUnusedSlot (which can hand back slot 0 and reject the item).
                if (this is EquipmentContainer && preferredSlot >= 0)
                    newSlot = preferredSlot;
                else
                    newSlot = GetUnusedSlot(preferredSlot);
            }

            if (newSlot < 0)
            {
                return false; // Inventory Full
            }
        }

        // Check if the newSlot fits
        if (!CanAccept(item, newSlot))
        {
            return false;
        }

        var itemTasks = new List<ItemTask>();
        var sourceItemTasks = new List<ItemTask>();

        if (canAddToSameSlot)
        {
            currentPreferredSlotItem.Count += item.Count;
            if (ContainerType != SlotType.None)
            {
                itemTasks.Add(new ItemCountUpdate(currentPreferredSlotItem, item.Count));
            }
        }
        else
        {
            item.SlotType = ContainerType;
            item.Slot = newSlot;
            item._holdingContainer = this;
            item.OwnerId = OwnerId;

            Items.Insert(0, item); // insert at front for easy buyback handling

            UpdateFreeSlotCount();

            // Note we use SlotType.None for things like the Item BuyBack Container. Make sure to manually handle the remove for these
            if (ContainerType != SlotType.None)
            {
                itemTasks.Add(new ItemAdd(item));
            }

            if (sourceContainer != this)
            {
                sourceContainer?.OnLeaveContainer(item, this, sourceSlot);
                OnEnterContainer(item, sourceContainer, sourceSlot);
            }
        }

        // Item Tasks
        if (sourceContainer != null && sourceContainer != this)
        {
            sourceContainer.Items.Remove(item);
            sourceContainer.UpdateFreeSlotCount();
            if (sourceContainer.ContainerType != SlotType.Mail)
            {
                sourceItemTasks.Add(new ItemRemoveSlot(item.Id, sourceSlotType, sourceSlot));
            }
        }

        // We use Invalid when doing internals, don't send to client
        if (taskType != ItemTaskType.Invalid)
        {
            if (itemTasks.Count > 0)
            {
                Owner?.SendPacket(new SCItemTaskSuccessPacket(taskType, itemTasks, []));
            }

            if (sourceItemTasks.Count > 0)
            {
                sourceContainer?.Owner?.SendPacket(new SCItemTaskSuccessPacket(taskType, sourceItemTasks, []));
            }
        }

        ApplyBindRules(taskType);

        // Moved to the end of the method so that the item is already in the inventory
        // Only trigger when moving between containers with different owners except for this being move to Mail container
        //if ((sourceContainer != this) && (item.OwnerId != OwnerId) && (this.ContainerType != SlotType.Mail))
        if (sourceContainer != this && ContainerType != SlotType.Mail)
        {
            Owner?.Inventory.OnAcquiredItem(item, item.Count);
        }
        else
        // Got attachment from Mail
        if (item.SlotType == SlotType.Mail && ContainerType != SlotType.Mail)
        {
            Owner?.Inventory.OnAcquiredItem(item, item.Count);
        }
        else
        // Adding mail attachment
        if (item.SlotType != SlotType.Mail && ContainerType == SlotType.Mail)
        {
            Owner?.Inventory.OnConsumedItem(item, item.Count);
        }

        return itemTasks.Count + sourceItemTasks.Count > 0;
    }

    /// <summary>
    /// Removes (and Destroys if needed) an item from the container
    /// </summary>
    /// <param name="task"></param>
    /// <param name="item">Item object to be removed</param>
    /// <param name="releaseIdAsWell">Set to true if this item needs to be removed from the world</param>
    /// <returns></returns>
    public bool RemoveItem(ItemTaskType task, Item item, bool releaseIdAsWell)
    {
        if (!item.CanDestroy())
        {
            return false;
        }

        var oldSlotNumber = (byte)item.Slot;

        // Handle items that can expire
        GamePacket sync = null;
        if (item.ExpirationOnlineMinutesLeft > 0.0 || item.ExpirationTime > DateTime.UtcNow || item.UnpackTime > DateTime.UtcNow)
        {
            sync = ItemManager.ExpireItemPacket(item);
        }

        if (sync != null)
        {
            Owner?.SendPacket(sync);
        }

        var res = item._holdingContainer.Items.Remove(item);
        if (res && task != ItemTaskType.Invalid)
        {
            // ItemAction.Remove (7) shares Take's apply path and RE-SETS the item into the slot
            // (live proof: server deleted purse 16777246, client ghost remained). Also forceRemove.
            item._holdingContainer?.Owner?.SendPacket(
                new SCItemTaskSuccessPacket(task, [new ItemRemoveSlot(item)], [item.Id]));
        }

        if (res && releaseIdAsWell)
        {
            item._holdingContainer = null;
            ItemManager.Instance.ReleaseId(item.Id);
        }

        UpdateFreeSlotCount();

        Owner?.Inventory.OnConsumedItem(item, item.Count);
        OnLeaveContainer(item, null, oldSlotNumber);

        return res;
    }

    /// <summary>
    /// Destroys amountToConsume amount of item units with template templateId from the container
    /// </summary>
    /// <param name="taskType"></param>
    /// <param name="templateId">Item templateId to search for</param>
    /// <param name="amountToConsume">Amount of item units to consume</param>
    /// <param name="preferredItem">If not null, use this Item as primary source for consume</param>
    /// <returns>The amount of items that was actually consumed, 0 when failed or not found</returns>
    public int ConsumeItem(ItemTaskType taskType, uint templateId, int amountToConsume, Item preferredItem)
    {
        if (!GetAllItemsByTemplate(templateId, -1, out var foundItems, out _))
        {
            return 0; // Nothing found
        }

        if (preferredItem != null && templateId != preferredItem.TemplateId)
        {
            return 0; // Preferred item template did not match the requested template
        }

        var totalConsumed = 0;
        var itemTasks = new List<ItemTask>();

        // Try to consume preferred item first
        if (amountToConsume > 0 && preferredItem != null)
        {
            // Remove this entry from our list
            if (!foundItems.Remove(preferredItem))
            {
                // Preferred item was not found in our list of found items, something is wrong here
                return 0;
            }

            var toRemove = Math.Min(preferredItem.Count, amountToConsume);
            preferredItem.Count -= toRemove;
            amountToConsume -= toRemove;

            if (preferredItem.Count > 0)
            {
                itemTasks.Add(new ItemCountUpdate(preferredItem, -toRemove));
            }
            else
            {
                RemoveItem(taskType, preferredItem, true); // Normally, this can never fail
            }

            Owner?.Inventory.OnConsumedItem(preferredItem, toRemove);

            totalConsumed += toRemove;
        }

        // Check all remaining items
        if (amountToConsume > 0)
        {
            foreach (var i in foundItems.OrderBy(x => x.Slot))
            {
                var toRemove = Math.Min(i.Count, amountToConsume);
                i.Count -= toRemove;
                amountToConsume -= toRemove;

                if (i.Count > 0)
                {
                    Owner?.Inventory.OnConsumedItem(i, toRemove);
                    itemTasks.Add(new ItemCountUpdate(i, -toRemove));
                }
                else
                {
                    RemoveItem(taskType, i, true); // Normally, this can never fail
                }

                totalConsumed += toRemove;
                if (amountToConsume <= 0)
                {
                    break; // We are done with the list, leave the rest as is
                }
            }
        }

        // RemoveItem already sent its own SCItemTaskSuccess (Remove + forceRemoves).
        // An empty follow-up packet is useless and can confuse client bag sync.
        if (taskType != ItemTaskType.Invalid && itemTasks.Count > 0)
        {
            Owner?.SendPacket(new SCItemTaskSuccessPacket(taskType, itemTasks, []));
        }

        UpdateFreeSlotCount();
        return totalConsumed;
    }

    /// <summary>
    /// Consumes exactly one unit from every explicitly selected stack as a single preflighted change.
    /// No item is touched when any selection is stale, duplicated, outside this container or cannot be
    /// destroyed. This is the transaction shape used by synthesis, whose request prices every slot.
    /// </summary>
    public bool TryConsumeExactItems(ItemTaskType taskType, IReadOnlyCollection<Item> selectedItems)
    {
        if (selectedItems is null || selectedItems.Count == 0)
            return false;

        if (!TryConsumeExactItemsCore(
                selectedItems.Select(item => (item, 1)).ToArray(),
                out var committedTasks))
            return false;

        PublishCommittedItemTasks(taskType, committedTasks);
        return true;
    }

    /// <summary>
    /// Consumes caller-selected item instances and amounts without publishing, appending their exact
    /// mutations to a larger transaction. This prevents a forged conversion request from substituting
    /// another stack with the same template id.
    /// </summary>
    public bool TryConsumeExactItemsIntoTaskBatch(
        IReadOnlyCollection<(Item Item, int Amount)> selectedItems,
        ICollection<ItemTask> tasks,
        ICollection<ulong> forceRemove)
    {
        if (tasks is null || forceRemove is null ||
            !TryConsumeExactItemsCore(selectedItems, out var committedTasks))
            return false;

        foreach (var (task, removedId) in committedTasks)
        {
            tasks.Add(task);
            if (removedId.HasValue)
                forceRemove.Add(removedId.Value);
        }

        return true;
    }

    /// <summary>
    /// Atomically consumes exact amounts by template across any number of stacks. All requirements
    /// are aggregated and preflighted under the container lock; a missing or non-destroyable stack
    /// leaves every item untouched. Awakening uses this instead of the generic post-effect consumer,
    /// so a result can never be committed while its scroll payment silently fails.
    /// </summary>
    public bool TryConsumeExactTemplates(
        ItemTaskType taskType,
        IReadOnlyCollection<(uint TemplateId, int Amount)> requirements)
    {
        if (!TryConsumeExactTemplatesCore(requirements, out var committedTasks))
            return false;

        PublishCommittedItemTasks(taskType, committedTasks);
        return true;
    }

    /// <summary>
    /// Atomically consumes exact template amounts without publishing a packet, appending the committed
    /// actions to a caller-owned item-task transaction instead. Gear Upgrade needs this form because its
    /// controller snapshots the target after the first Socketing transaction it receives; publishing the
    /// wallet, reagent and target as separate transactions leaves the selected socket frame one step behind.
    /// </summary>
    public bool TryConsumeExactTemplatesIntoTaskBatch(
        IReadOnlyCollection<(uint TemplateId, int Amount)> requirements,
        ICollection<ItemTask> tasks,
        ICollection<ulong> forceRemove)
    {
        if (tasks is null || forceRemove is null ||
            !TryConsumeExactTemplatesCore(requirements, out var committedTasks))
            return false;

        foreach (var (task, removedId) in committedTasks)
        {
            tasks.Add(task);
            if (removedId.HasValue)
                forceRemove.Add(removedId.Value);
        }

        return true;
    }

    /// <summary>
    /// Checks whether aggregated default-item rewards fit after a caller-owned transaction releases
    /// a known number of slots. Existing compatible stacks are filled before new slots are counted.
    /// </summary>
    public bool CanAcquireDefaultTemplates(
        IReadOnlyCollection<(uint TemplateId, int Amount)> rewards,
        int additionallyFreedSlots = 0)
    {
        if (rewards is null || additionallyFreedSlots < 0)
            return false;
        if (rewards.Count == 0)
            return true;

        var aggregated = new Dictionary<uint, int>();
        try
        {
            foreach (var (templateId, amount) in rewards)
            {
                if (templateId == 0 || amount <= 0)
                    return false;
                aggregated[templateId] = checked(aggregated.GetValueOrDefault(templateId) + amount);
            }
        }
        catch (OverflowException)
        {
            return false;
        }

        lock (Items)
        {
            var freeSlots = FreeSlotCount + additionallyFreedSlots;
            foreach (var (templateId, amount) in aggregated)
            {
                var template = ItemManager.Instance.GetTemplate(templateId);
                if (template is null || template.MaxCount <= 0)
                    return false;

                var stackSpace = Items
                    .Where(item => item.TemplateId == templateId)
                    .Sum(item => Math.Max(0, template.MaxCount - item.Count));
                var remaining = Math.Max(0, amount - stackSpace);
                var slotsNeeded = (remaining + template.MaxCount - 1) / template.MaxCount;
                freeSlots -= slotsNeeded;
                if (freeSlots < 0)
                    return false;
            }

            return true;
        }
    }

    /// <summary>
    /// Acquires preflighted default items without publishing packets and appends the exact Add/Take
    /// actions to a caller-owned transaction. A caller combining this with consumption should hold
    /// the <see cref="Items"/> monitor across preflight and both commits.
    /// </summary>
    public bool TryAcquireDefaultTemplatesIntoTaskBatch(
        IReadOnlyCollection<(uint TemplateId, int Amount)> rewards,
        ICollection<ItemTask> tasks)
    {
        if (rewards is null || tasks is null)
            return false;
        if (rewards.Count == 0)
            return true;

        Dictionary<uint, int> aggregated;
        try
        {
            aggregated = rewards
                .GroupBy(entry => entry.TemplateId)
                .ToDictionary(
                    group => group.Key,
                    group => group.Aggregate(0, (total, entry) => checked(total + entry.Amount)));
        }
        catch (OverflowException)
        {
            return false;
        }

        var aggregateRows = aggregated.Select(entry => (entry.Key, entry.Value)).ToArray();
        if (!CanAcquireDefaultTemplates(aggregateRows))
            return false;

        lock (Items)
        {
            foreach (var (templateId, amount) in aggregated)
            {
                var oldCounts = Items
                    .Where(item => item.TemplateId == templateId)
                    .ToDictionary(item => item.Id, item => item.Count);
                if (!AcquireDefaultItemEx(
                        ItemTaskType.Invalid,
                        templateId,
                        amount,
                        -1,
                        out var newItems,
                        out var updatedItems,
                        0))
                    return false;

                foreach (var item in updatedItems)
                    tasks.Add(new ItemCountUpdate(item, item.Count - oldCounts.GetValueOrDefault(item.Id)));
                foreach (var item in newItems)
                    tasks.Add(new ItemAdd(item));
            }
        }

        return true;
    }

    /// <summary>
    /// Checks grade-aware rewards against compatible stacks and slots released by the same transaction.
    /// </summary>
    public bool CanAcquireDefaultItems(
        IReadOnlyCollection<(uint TemplateId, int Amount, int Grade)> rewards,
        int additionallyFreedSlots = 0,
        bool preserveExplicitGrade = false)
    {
        if (rewards is null || additionallyFreedSlots < 0)
            return false;
        if (rewards.Count == 0)
            return true;

        var normalized = new List<(uint TemplateId, int Amount, int Grade)>(rewards.Count);
        try
        {
            foreach (var entry in rewards)
            {
                var template = ItemManager.Instance.GetTemplate(entry.TemplateId);
                if (entry.TemplateId == 0 || entry.Amount <= 0 || template is null)
                    return false;
                normalized.Add((
                    entry.TemplateId,
                    entry.Amount,
                    NormalizeDefaultGrade(template, entry.Grade, preserveExplicitGrade)));
            }
        }
        catch (OverflowException)
        {
            return false;
        }

        Dictionary<(uint TemplateId, int Grade), int> aggregated;
        try
        {
            aggregated = normalized
                .GroupBy(entry => (entry.TemplateId, entry.Grade))
                .ToDictionary(
                    group => group.Key,
                    group => group.Aggregate(0, (total, entry) => checked(total + entry.Amount)));
        }
        catch (OverflowException)
        {
            return false;
        }

        lock (Items)
        {
            var freeSlots = FreeSlotCount + additionallyFreedSlots;
            foreach (var ((templateId, grade), amount) in aggregated)
            {
                var template = ItemManager.Instance.GetTemplate(templateId);
                if (template is null || template.MaxCount <= 0)
                    return false;
                var stackSpace = Items
                    .Where(item => item.TemplateId == templateId && item.Grade == grade)
                    .Sum(item => Math.Max(0, template.MaxCount - item.Count));
                var remaining = Math.Max(0, amount - stackSpace);
                freeSlots -= (remaining + template.MaxCount - 1) / template.MaxCount;
                if (freeSlots < 0)
                    return false;
            }
            return true;
        }
    }

    /// <summary>Acquires grade-aware, preflighted rewards into a caller-owned item-task batch.</summary>
    public bool TryAcquireDefaultItemsIntoTaskBatch(
        IReadOnlyCollection<(uint TemplateId, int Amount, int Grade)> rewards,
        ICollection<ItemTask> tasks,
        uint crafterId = 0,
        bool preserveExplicitGrade = false)
    {
        if (rewards is null || tasks is null ||
            !CanAcquireDefaultItems(rewards, preserveExplicitGrade: preserveExplicitGrade))
            return false;
        if (rewards.Count == 0)
            return true;

        var aggregated = rewards
            .GroupBy(entry => (entry.TemplateId, Grade: NormalizeDefaultGrade(
                ItemManager.Instance.GetTemplate(entry.TemplateId), entry.Grade,
                preserveExplicitGrade)))
            .Select(group => (group.Key.TemplateId, Amount: group.Sum(entry => entry.Amount), group.Key.Grade));

        lock (Items)
        {
            foreach (var (templateId, amount, grade) in aggregated)
            {
                var oldCounts = Items
                    .Where(item => item.TemplateId == templateId && item.Grade == grade)
                    .ToDictionary(item => item.Id, item => item.Count);
                if (!AcquireDefaultItemEx(
                        ItemTaskType.Invalid,
                        templateId,
                        amount,
                        grade,
                        out var newItems,
                        out var updatedItems,
                        crafterId,
                        preserveExplicitGrade: preserveExplicitGrade))
                    return false;
                foreach (var item in updatedItems)
                    tasks.Add(new ItemCountUpdate(item, item.Count - oldCounts.GetValueOrDefault(item.Id)));
                foreach (var item in newItems)
                    tasks.Add(new ItemAdd(item));
            }
        }

        return true;
    }

    /// <summary>
    /// Atomically exchanges the exact material totals for the products of one preplanned AA10 craft.
    /// Capacity is simulated after consumption and all mutations are committed under the container
    /// lock. Packets are intentionally left to the caller so observers never see a partial state.
    /// </summary>
    public bool TryExchangeCraftItems(
        CraftTransactionPlan plan,
        uint crafterId,
        ICollection<ItemTask> consumeTasks,
        ICollection<ulong> forceRemove,
        ICollection<ItemTask> rewardTasks,
        out CraftFailure failure) =>
        TryExchangeCraftItems(
            plan, crafterId, null, false, consumeTasks, forceRemove, rewardTasks,
            out failure);

    /// <summary>
    /// Atomically exchanges bag materials and bag/equipment products for one AA10 craft. An
    /// auto-equipped backpack may replace an equipped glider only when the post-consumption bag
    /// has room for that glider; an existing trade pack or an active glide fails closed.
    /// </summary>
    public bool TryExchangeCraftItems(
        CraftTransactionPlan plan,
        uint crafterId,
        ItemContainer equipment,
        bool isGliding,
        ICollection<ItemTask> consumeTasks,
        ICollection<ulong> forceRemove,
        ICollection<ItemTask> rewardTasks,
        out CraftFailure failure)
    {
        failure = CraftFailure.None;
        if (plan is null || plan.Materials.Count == 0 ||
            (plan.Products.Count == 0 && plan.FailedProductItemIds.Count == 0) ||
            consumeTasks is null || forceRemove is null || rewardTasks is null)
        {
            failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
            return false;
        }

        var requirements = plan.Materials.Select(entry =>
            (entry.ItemId, entry.Amount, entry.Grade)).ToArray();
        var rewards = plan.Products.Select(entry =>
            (entry.ItemId, entry.Amount, entry.Grade, entry.AutoEquipBackpack)).ToArray();

        lock (Items)
        {
            if (equipment is null)
                return TryExchangeCraftItemsCore(
                    plan, crafterId, null, isGliding, requirements, rewards,
                    consumeTasks, forceRemove, rewardTasks, out failure);

            lock (equipment.Items)
            {
                return TryExchangeCraftItemsCore(
                    plan, crafterId, equipment, isGliding, requirements, rewards,
                    consumeTasks, forceRemove, rewardTasks, out failure);
            }
        }
    }

    private bool TryExchangeCraftItemsCore(
        CraftTransactionPlan plan,
        uint crafterId,
        ItemContainer equipment,
        bool isGliding,
        IReadOnlyCollection<(uint ItemId, int Amount, int Grade)> requirements,
        IReadOnlyCollection<(uint ItemId, int Amount, int Grade, bool AutoEquipBackpack)> rewards,
        ICollection<ItemTask> consumeTasks,
        ICollection<ulong> forceRemove,
        ICollection<ItemTask> rewardTasks,
        out CraftFailure failure)
    {
        if (!CanExchangeCraftItems(
                requirements, rewards, equipment, isGliding,
                out var selectedItems, out var equippedGlider, out failure))
            return false;

        if (!TryConsumeExactItemsIntoTaskBatch(selectedItems, consumeTasks, forceRemove))
        {
            failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
            return false;
        }

        if (equippedGlider is not null)
        {
            var equipmentSlot = (byte)equippedGlider.Slot;
            if (!AddOrMoveExistingItem(ItemTaskType.Invalid, equippedGlider))
                throw new InvalidOperationException(
                    $"Preflighted AA10 craft {plan.CraftId} could not move its equipped glider.");
            rewardTasks.Add(new ItemAdd(equippedGlider));
            rewardTasks.Add(new ItemRemoveSlot(
                equippedGlider.Id, SlotType.Equipment, equipmentSlot));
        }

        var bagRewards = rewards
            .Where(entry => !entry.AutoEquipBackpack)
            .Select(entry => (entry.ItemId, entry.Amount, entry.Grade))
            .ToArray();
        if (bagRewards.Length > 0 &&
            !TryAcquireDefaultItemsIntoTaskBatch(
                bagRewards, rewardTasks, crafterId, preserveExplicitGrade: true))
            throw new InvalidOperationException(
                $"Preflighted AA10 craft {plan.CraftId} could not acquire its bag products.");

        var backpackRewards = rewards
            .Where(entry => entry.AutoEquipBackpack)
            .Select(entry => (entry.ItemId, entry.Amount, entry.Grade))
            .ToArray();
        if (backpackRewards.Length > 0 &&
            (equipment is null || !equipment.TryAcquireDefaultItemsIntoTaskBatch(
                backpackRewards, rewardTasks, crafterId, preserveExplicitGrade: true)))
            throw new InvalidOperationException(
                $"Preflighted AA10 craft {plan.CraftId} could not equip its backpack product.");

        return true;
    }

    private bool CanExchangeCraftItems(
        IReadOnlyCollection<(uint ItemId, int Amount, int Grade)> requirements,
        IReadOnlyCollection<(uint ItemId, int Amount, int Grade, bool AutoEquipBackpack)> rewards,
        ItemContainer equipment,
        bool isGliding,
        out IReadOnlyCollection<(Item Item, int Amount)> selectedItems,
        out Item equippedGlider,
        out CraftFailure failure)
    {
        selectedItems = [];
        equippedGlider = null;
        failure = CraftFailure.None;
        var remaining = Items
            .OrderBy(item => item.Slot)
            .Select(item => new CraftExchangeStack(item, item.Count))
            .ToList();
        var selected = new Dictionary<Item, int>();

        foreach (var (itemId, amount, grade) in requirements)
        {
            if (itemId == 0 || amount <= 0 || grade < 0)
            {
                failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
                return false;
            }

            var needed = amount;
            foreach (var stack in remaining.Where(entry =>
                         entry.Item.TemplateId == itemId && entry.Item.Grade == grade &&
                         entry.Count > 0))
            {
                var consumed = Math.Min(stack.Count, needed);
                if (consumed == stack.Count && !stack.Item.CanDestroy())
                {
                    failure = new CraftFailure(CraftFailureCode.ItemNotDestroyable);
                    return false;
                }
                stack.Count -= consumed;
                needed -= consumed;
                selected[stack.Item] = selected.GetValueOrDefault(stack.Item) + consumed;
                if (needed == 0)
                    break;
            }
            if (needed != 0)
            {
                failure = new CraftFailure(CraftFailureCode.MissingMaterials);
                return false;
            }
        }

        var backpackRewards = rewards.Where(entry => entry.AutoEquipBackpack).ToArray();
        if (backpackRewards.Length > 1 || backpackRewards.Any(entry => entry.Amount != 1))
        {
            failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
            return false;
        }
        if (backpackRewards.Length == 1)
        {
            var reward = backpackRewards[0];
            var template = ItemManager.Instance.GetTemplate(reward.ItemId);
            if (equipment is not EquipmentContainer || template is not BackpackTemplate ||
                !ItemManager.Instance.IsAutoEquipTradePack(reward.ItemId))
            {
                failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
                return false;
            }
            if (isGliding)
            {
                failure = new CraftFailure(CraftFailureCode.CannotChangeBackpackInGliding);
                return false;
            }

            var equipped = equipment.GetItemBySlot((int)EquipmentItemSlot.Backpack);
            if (equipped is not null)
            {
                if (equipped.Template is not BackpackTemplate
                    { BackpackType: BackpackType.Glider })
                {
                    failure = new CraftFailure(CraftFailureCode.BackpackOccupied);
                    return false;
                }
                equippedGlider = equipped;
            }
        }

        var freeSlots = FreeSlotCount + remaining.Count(entry => entry.Count == 0);
        if (equippedGlider is not null && --freeSlots < 0)
        {
            failure = new CraftFailure(CraftFailureCode.BagFull);
            return false;
        }

        foreach (var (itemId, amount, requestedGrade, autoEquipBackpack) in rewards)
        {
            var template = ItemManager.Instance.GetTemplate(itemId);
            if (itemId == 0 || amount <= 0 || requestedGrade < 0 || template is null ||
                template.MaxCount <= 0 ||
                autoEquipBackpack != ItemManager.Instance.IsAutoEquipTradePack(itemId))
            {
                failure = new CraftFailure(CraftFailureCode.ConcurrentChange);
                return false;
            }
            if (autoEquipBackpack)
                continue;

            var grade = requestedGrade;
            var stackSpace = remaining
                .Where(entry => entry.Count > 0 && entry.Item.TemplateId == itemId &&
                                entry.Item.Grade == grade)
                .Sum(entry => Math.Max(0L, (long)template.MaxCount - entry.Count));
            var remainder = Math.Max(0L, (long)amount - stackSpace);
            var requiredSlots = (remainder + template.MaxCount - 1) / template.MaxCount;
            if (requiredSlots > freeSlots)
            {
                failure = new CraftFailure(CraftFailureCode.BagFull);
                return false;
            }
            freeSlots -= (int)requiredSlots;
        }

        selectedItems = selected.Select(entry => (entry.Key, entry.Value)).ToArray();
        return true;
    }

    private sealed class CraftExchangeStack(Item item, int count)
    {
        public Item Item { get; } = item;
        public int Count { get; set; } = count;
    }

    private bool TryConsumeExactItemsCore(
        IReadOnlyCollection<(Item Item, int Amount)> selectedItems,
        out List<(ItemTask Task, ulong? RemovedId)> committedTasks)
    {
        committedTasks = [];
        if (selectedItems is null || selectedItems.Count == 0)
            return false;

        lock (Items)
        {
            var uniqueIds = new HashSet<ulong>();
            foreach (var (item, amount) in selectedItems)
            {
                if (item is null || amount <= 0 || !uniqueIds.Add(item.Id) || item.Count < amount ||
                    !ReferenceEquals(item._holdingContainer, this) || !Items.Contains(item) ||
                    (item.Count == amount && !item.CanDestroy()))
                    return false;
            }

            var snapshots = selectedItems
                .Select(entry => (entry.Item, OldCount: entry.Item.Count, entry.Amount, Slot: (byte)entry.Item.Slot))
                .ToList();
            var removed = new List<Item>();
            try
            {
                foreach (var entry in snapshots)
                {
                    entry.Item.Count -= entry.Amount;
                    if (entry.Item.Count == 0)
                    {
                        if (!Items.Remove(entry.Item))
                            throw new InvalidOperationException(
                                $"Selected item {entry.Item.Id} left its container during consumption.");
                        removed.Add(entry.Item);
                    }
                }
            }
            catch (Exception exception)
            {
                foreach (var entry in snapshots)
                    entry.Item.Count = entry.OldCount;
                foreach (var item in removed)
                    if (!Items.Contains(item))
                        Items.Add(item);
                Logger.Error(exception, "Exact item consumption rolled back before commit");
                return false;
            }

            committedTasks = new List<(ItemTask Task, ulong? RemovedId)>(snapshots.Count);
            foreach (var entry in snapshots)
            {
                Owner?.Inventory.OnConsumedItem(entry.Item, entry.Amount);
                if (entry.OldCount > entry.Amount)
                {
                    committedTasks.Add((new ItemCountUpdate(entry.Item, -entry.Amount), null));
                    continue;
                }

                committedTasks.Add((new ItemRemoveSlot(entry.Item), entry.Item.Id));
                entry.Item._holdingContainer = null;
                ItemManager.Instance.ReleaseId(entry.Item.Id);
                OnLeaveContainer(entry.Item, null, entry.Slot);
            }

            UpdateFreeSlotCount();
            return true;
        }
    }

    private static int NormalizeDefaultGrade(
        ItemTemplate template,
        int requestedGrade,
        bool preserveExplicitGrade = false)
    {
        if (template is null)
            return requestedGrade;
        if (preserveExplicitGrade && requestedGrade >= 0)
            return requestedGrade;
        if (template.FixedGrade >= 0 && !template.Gradable)
            return template.FixedGrade;
        if (requestedGrade < 0)
            requestedGrade = template.FixedGrade;
        return Math.Max(0, requestedGrade);
    }

    private bool TryConsumeExactTemplatesCore(
        IReadOnlyCollection<(uint TemplateId, int Amount)> requirements,
        out List<(ItemTask Task, ulong? RemovedId)> committedTasks)
    {
        committedTasks = [];
        if (requirements is null || requirements.Count == 0)
            return false;

        var aggregated = new Dictionary<uint, int>();
        try
        {
            foreach (var (templateId, amount) in requirements)
            {
                if (templateId == 0 || amount <= 0)
                    return false;
                aggregated[templateId] = checked(aggregated.GetValueOrDefault(templateId) + amount);
            }
        }
        catch (OverflowException)
        {
            return false;
        }

        lock (Items)
        {
            var plan = new List<(Item Item, int OldCount, int Amount, byte Slot)>();
            foreach (var (templateId, requiredAmount) in aggregated)
            {
                var remaining = requiredAmount;
                foreach (var item in Items.Where(entry => entry.TemplateId == templateId && entry.Count > 0)
                             .OrderBy(entry => entry.Slot))
                {
                    var amount = Math.Min(item.Count, remaining);
                    if (amount == item.Count && !item.CanDestroy())
                        return false;

                    plan.Add((item, item.Count, amount, (byte)item.Slot));
                    remaining -= amount;
                    if (remaining == 0)
                        break;
                }

                if (remaining != 0)
                    return false;
            }

            var removed = new List<Item>();
            try
            {
                foreach (var entry in plan)
                {
                    entry.Item.Count -= entry.Amount;
                    if (entry.Item.Count == 0)
                    {
                        if (!Items.Remove(entry.Item))
                            throw new InvalidOperationException(
                                $"Required item {entry.Item.Id} left its container during consumption.");
                        removed.Add(entry.Item);
                    }
                }
            }
            catch (Exception exception)
            {
                foreach (var entry in plan)
                    entry.Item.Count = entry.OldCount;
                foreach (var item in removed)
                    if (!Items.Contains(item))
                        Items.Add(item);
                Logger.Error(exception, "Exact template consumption rolled back before commit");
                return false;
            }

            committedTasks = new List<(ItemTask Task, ulong? RemovedId)>(plan.Count);
            foreach (var entry in plan)
            {
                Owner?.Inventory.OnConsumedItem(entry.Item, entry.Amount);
                if (entry.OldCount > entry.Amount)
                {
                    committedTasks.Add((new ItemCountUpdate(entry.Item, -entry.Amount), null));
                    continue;
                }

                committedTasks.Add((new ItemRemoveSlot(entry.Item), entry.Item.Id));
                entry.Item._holdingContainer = null;
                ItemManager.Instance.ReleaseId(entry.Item.Id);
                OnLeaveContainer(entry.Item, null, entry.Slot);
            }

            UpdateFreeSlotCount();
            return true;
        }
    }

    /// <summary>
    /// Publishes already committed inventory mutations one item per packet. In r575, Take (action 6)
    /// has a variable-sized full-item body. A synthesis packet containing several Take tasks updates
    /// only its first stack even though every server mutation persists; the missing decrements appear
    /// after relog. Framing each committed task separately preserves the atomic server transaction and
    /// gives every body a fresh packet boundary. AA8 solved the same visible-state problem with its
    /// signed AddStack action, but that action is not wire-compatible with AA10.
    /// </summary>
    private void PublishCommittedItemTasks(
        ItemTaskType taskType,
        IReadOnlyCollection<(ItemTask Task, ulong? RemovedId)> committedTasks)
    {
        if (taskType == ItemTaskType.Invalid || Owner is null)
            return;

        foreach (var packet in BuildCommittedItemTaskPackets(taskType, committedTasks))
            Owner.SendPacket(packet);
    }

    internal static IReadOnlyList<SCItemTaskSuccessPacket> BuildCommittedItemTaskPackets(
        ItemTaskType taskType,
        IReadOnlyCollection<(ItemTask Task, ulong? RemovedId)> committedTasks)
    {
        if (taskType == ItemTaskType.Invalid || committedTasks is null || committedTasks.Count == 0)
            return [];

        return committedTasks.Select(entry => new SCItemTaskSuccessPacket(
            taskType,
            [entry.Task],
            entry.RemovedId.HasValue ? [entry.RemovedId.Value] : [])).ToList();
    }

    /// <summary>
    /// Frames a caller-owned transaction one action per packet while pairing each Seize with its exact
    /// forced-removal id. This is required when two selected stacks both become AA10 Take bodies.
    /// </summary>
    internal static IReadOnlyList<SCItemTaskSuccessPacket> BuildIndependentItemTaskPackets(
        ItemTaskType taskType,
        IReadOnlyCollection<ItemTask> tasks,
        IReadOnlyCollection<ulong> forceRemove)
    {
        if (taskType == ItemTaskType.Invalid || tasks is null || tasks.Count == 0)
            return [];

        forceRemove ??= [];
        var removeTasks = tasks.Count(task => task is ItemRemoveSlot);
        if (removeTasks != forceRemove.Count)
            throw new ArgumentException(
                $"Item task batch has {removeTasks} Seize actions but {forceRemove.Count} forced removals.");

        var removedIds = new Queue<ulong>(forceRemove);
        return tasks.Select(task => new SCItemTaskSuccessPacket(
            taskType,
            [task],
            task is ItemRemoveSlot ? [removedIds.Dequeue()] : [])).ToList();
    }

    /// <summary>
    /// Adds items to container using templateId and gradeToAdd, if items aren't full stacks, those will be updated first, new items will be generated for the remaining amounts
    /// </summary>
    /// <param name="taskType"></param>
    /// <param name="templateId">Item templateId use for adding</param>
    /// <param name="amountToAdd">Number of item units to add</param>
    /// <param name="gradeToAdd">Overrides default grade if possible</param>
    /// <param name="crafterId"></param>
    /// <returns></returns>
    public bool AcquireDefaultItem(ItemTaskType taskType, uint templateId, int amountToAdd, int gradeToAdd = -1,
        uint crafterId = 0)
    {
        return AcquireDefaultItemEx(taskType, templateId, amountToAdd, gradeToAdd, out _, out _, crafterId);
    }

    /// <summary>
    /// Adds items to container using templateId and gradeToAdd, if items aren't full stacks, those will be updated first, new items will be generated for the remaining amounts
    /// </summary>
    /// <param name="taskType"></param>
    /// <param name="templateId">Item templateId use for adding</param>
    /// <param name="amountToAdd">Number of item units to add</param>
    /// <param name="gradeToAdd">Overrides default grade if possible</param>
    /// <param name="newItemsList"></param>
    /// <param name="updatedItemsList">A List of the newly added or updated items</param>
    /// <param name="crafterId"></param>
    /// <param name="preferredSlot"></param>
    /// <returns></returns>
    public bool AcquireDefaultItemEx(
        ItemTaskType taskType,
        uint templateId,
        int amountToAdd,
        int gradeToAdd,
        out List<Item> newItemsList,
        out List<Item> updatedItemsList,
        uint crafterId,
        int preferredSlot = -1,
        bool preserveExplicitGrade = false)
    {
        newItemsList = [];
        updatedItemsList = [];
        if (amountToAdd <= 0)
        {
            return true;
        }

        GetAllItemsByTemplate(templateId, gradeToAdd, out var currentItems, out var currentTotalItemCount);
        var template = ItemManager.Instance.GetTemplate(templateId);
        if (template == null)
        {
            return false; // Invalid item templateId
        }

        var totalFreeSpaceForThisItem = currentItems.Count * template.MaxCount - currentTotalItemCount + FreeSlotCount * template.MaxCount;

        // Trying to add too many item units to this container ?
        if (amountToAdd > totalFreeSpaceForThisItem)
        {
            return false;
        }

        // Calculate grade to actually add for new items
        if (!preserveExplicitGrade && template.FixedGrade >= 0 && template.Gradable == false)
        {
            gradeToAdd = template.FixedGrade;
        }

        if (gradeToAdd == -1)
        {
            gradeToAdd = template.FixedGrade;
        }

        if (gradeToAdd < 0)
        {
            gradeToAdd = 0;
        }

        // First try to add to existing item counts
        var itemTasks = new List<ItemTask>();

        // Never update in mail or auction containers
        if (ContainerType != SlotType.Mail && ContainerType != SlotType.Auction)
        {
            foreach (var i in currentItems.OrderBy(x => x.Slot))
            {
                var freeSpace = i.Template.MaxCount - i.Count;
                if (freeSpace > 0)
                {
                    var addAmount = Math.Min(freeSpace, amountToAdd);
                    i.Count += addAmount;
                    amountToAdd -= addAmount;
                    itemTasks.Add(new ItemCountUpdate(i, addAmount));
                    updatedItemsList.Add(i);
                    Owner?.Inventory.OnAcquiredItem(i, addAmount, true);
                }

                if (amountToAdd < 0)
                {
                    break;
                }
            }
        }

        var syncPackets = new List<GamePacket>();
        while (amountToAdd > 0)
        {
            var addAmount = Math.Min(amountToAdd, template.MaxCount);
            var newItem = preserveExplicitGrade
                ? ItemManager.Instance.CreateCraftProduct(templateId, addAmount, (byte)gradeToAdd)
                : ItemManager.Instance.Create(templateId, addAmount, (byte)gradeToAdd);
            if (newItem == null)
            {
                Logger.Error($"Failed to add item with ID {templateId}, possible duplicate entries!");
                return false;
            }

            // Add name if marked as crafter (single stack items only)
            if (crafterId > 0 && newItem.Template.MaxCount == 1)
            {
                newItem.MadeUnitId = crafterId;
                newItem.WorldId =
                    (byte)WorldManager
                        .DefaultWorldTemplateId; // TODO: proper world id handling, this should actually be the ServerId
            }

            amountToAdd -= addAmount;
            var prefSlot = preferredSlot;
            if (newItem.Template is BackpackTemplate && ContainerType == SlotType.Equipment)
            {
                prefSlot = (int)EquipmentItemSlot.Backpack;
            }

            // Timers
            if (newItem.Template.ExpAbsLifetime > 0)
            {
                syncPackets.Add(ItemManager.SetItemExpirationTime(newItem, DateTime.UtcNow.AddMinutes(newItem.Template.ExpAbsLifetime)));
            }

            if (newItem.Template.ExpOnlineLifetime > 0)
            {
                syncPackets.Add(ItemManager.SetItemOnlineExpirationTime(newItem, newItem.Template.ExpOnlineLifetime));
            }

            if (newItem.Template.ExpDate > DateTime.MinValue)
            {
                syncPackets.Add(ItemManager.SetItemExpirationTime(newItem, newItem.Template.ExpDate));
            }

            if (newItem is EquipItem equipItem && newItem.Template is EquipItemTemplate equipItemTemplate)
            {
                equipItem.ChargeCount = equipItemTemplate.ChargeCount;
                if (equipItemTemplate.ChargeLifetime > 0 && equipItemTemplate.BindType.HasFlag(ItemBindType.BindOnUnpack) == false)
                {
                    equipItem.ChargeStartTime = DateTime.UtcNow;
                }
            }

            if (AddOrMoveExistingItem(ItemTaskType.Invalid, newItem, prefSlot)) // Task set to invalid as we send our own packets inside this function
            {
                itemTasks.Add(new ItemAdd(newItem));
                newItemsList.Add(newItem);
            }
            else
            {
                throw new GameException("AcquireDefaultItem(); Unable to add new items"); // Inventory should have enough space, something went wrong
            }
        }

        if (taskType != ItemTaskType.Invalid)
        {
            Owner?.SendPacket(new SCItemTaskSuccessPacket(taskType, itemTasks, []));
        }

        UpdateFreeSlotCount();

        // Send item expire packets if needed
        foreach (var sync in syncPackets)
        {
            if (sync != null)
            {
                Owner?.SendPacket(sync);
            }
        }

        return itemTasks.Count > 0;
    }

    /// <summary>
    /// Count the maximum amount of items of a given templateID that can be added to an inventory taking into account the max stack size. Ignores item grade
    /// </summary>
    /// <param name="templateId">Item template ID</param>
    /// <returns>Amount of item units that can be added before the bag is full</returns>
    public int SpaceLeftForItem(uint templateId)
    {
        var template = ItemManager.Instance.GetTemplate(templateId);
        if (template == null)
        {
            return 0; // Invalid item templateId
        }

        // Special handling for money
        if (templateId == Item.Coins)
        {
            return CalculateSpaceLeftForMoney(template.MaxCount);
        }

        GetAllItemsByTemplate(templateId, -1, out var currentItems, out var currentTotalItemCount);
        return ClampedSpaceLeft(currentItems.Count, currentTotalItemCount, template.MaxCount);
    }

    /// <summary>
    /// Slots-times-stack-size worked out in long and clamped back into int.
    ///
    /// items.max_stack_size reaches int.MaxValue — money (500), Lulu's leaflet (28586) and cash (28851) all
    /// carry it, and only money is special-cased away from this path. Doing the two multiplications in int
    /// overflows as soon as more than one slot is involved, and an unlimited container reports 9999 free
    /// slots, so it wraps immediately. A wrapped negative reads as "no room" and silently refuses a valid
    /// item; a wrapped positive promises room that is not there and fails later during the actual move.
    /// </summary>
    private int ClampedSpaceLeft(int matchingSlots, int currentTotalItemCount, int maxCount)
    {
        var space = (long)matchingSlots * maxCount - currentTotalItemCount + (long)FreeSlotCount * maxCount;
        return (int)Math.Clamp(space, 0, int.MaxValue);
    }

    /// <summary>
    /// Count the maximum amount of items of a given item that can be added to an inventory taking into account the max stack size using a specific item to be added. Takes into account item grade
    /// </summary>
    /// <param name="itemToAdd">Item we wish to add for</param>
    /// <param name="currentItems">List of items in the current container that match the itemToAdd criteria (template and grade)</param>
    /// <returns>Amount of item units of the given item that can be added before the bag is full</returns>
    public int SpaceLeftForItem(Item itemToAdd, out List<Item> currentItems)
    {
        if (itemToAdd == null)
        {
            currentItems = [];
            return 0;
        }

        if (SpaceLeftForMoney(itemToAdd, out currentItems, out var spaceLeftForItem))
        {
            return spaceLeftForItem;
        }

        GetAllItemsByTemplate(itemToAdd.TemplateId, itemToAdd.Grade, out currentItems, out var currentTotalItemCount);
        return ClampedSpaceLeft(currentItems.Count, currentTotalItemCount, itemToAdd.Template.MaxCount);
    }

    private bool SpaceLeftForMoney(Item itemToAdd, out List<Item> currentItems, out int spaceLeftForItem)
    {
        if (itemToAdd.TemplateId == Item.Coins)
        {
            currentItems = [itemToAdd];
            spaceLeftForItem = CalculateSpaceLeftForMoney(itemToAdd.Template.MaxCount);
            return true;
        }

        currentItems = null;
        spaceLeftForItem = 0;
        return false;
    }

    /// <summary>
    /// Calculates how much more money can be added based on the owner's balance and max stack size.
    /// Always returns value >= 0
    /// </summary>
    /// <param name="maxCount">Maximum stack size for money item</param>
    /// <returns>Space left for money</returns>
    private int CalculateSpaceLeftForMoney(int maxCount)
    {
        // Ensure non-negative money value
        var moneyCount = Math.Max(0L, _owner.Money);

        // Clamp to MaxCount and int range
        var count = (int)Math.Min(moneyCount, maxCount);

        // How many more can be added (always >= 0)
        return maxCount - count;
    }

    /// <summary>
    /// Returns a list of items in the order of their slot, unused slots return null
    /// </summary>
    /// <returns>Ordered list slots with items</returns>
    public List<Item> GetSlottedItemsList()
    {
        var res = new List<Item>(ContainerSize);
        for (var i = 0; i < ContainerSize; i++)
        {
            res.Add(GetItemBySlot(i));
        }

        return res;
    }

    /// <summary>
    /// Searches container for a list of items that have a specified templateId
    /// </summary>
    /// <param name="templateId">templateId to search for</param>
    /// <param name="foundItems">List of found item objects</param>
    /// <param name="gradeToFind">Only lists items of specific grade equal to gradeToFind or any grade if -1 was provided</param>
    /// <param name="unitsOfItemFound">Total count of the count values of the found items</param>
    /// <returns>True if any item was found</returns>
    public bool GetAllItemsByTemplate(uint templateId, int gradeToFind, out List<Item> foundItems, out int unitsOfItemFound)
    {
        foundItems = [];
        unitsOfItemFound = 0;
        foreach (var i in Items)
        {
            if (i.TemplateId == templateId && (gradeToFind < 0 || gradeToFind == i.Grade))
            {
                foundItems.Add(i);
                unitsOfItemFound += i.Count;
            }
        }

        return foundItems.Count > 0;
    }

    /// <summary>
    /// Apply Bound flag to items when needed by the container (BindOnPickup, BindOnEquip)
    /// </summary>
    /// <param name="taskType"></param>
    public void ApplyBindRules(ItemTaskType taskType)
    {
        var itemTasks = new List<ItemTask>();
        foreach (var item in Items)
        {
            if (item.HasFlag(ItemFlag.SoulBound))
                continue;

            var bound = false;
            if (ContainerType == SlotType.Inventory && item.Template.BindType == ItemBindType.BindOnPickup)
            {
                item.SetFlag(ItemFlag.SoulBound);
                bound = true;
            }

            // Character gear, mate gear, and ship parts all count as equipping for BindOnEquip.
            // EquipmentSlave used to be skipped, so the client kept showing the bind confirm dialog
            // (template is BoE, SoulBound never set) every time a part was put on the hull.
            if (!bound &&
                item.Template.BindType == ItemBindType.BindOnEquip &&
                ContainerType is SlotType.Equipment or SlotType.EquipmentSlave or SlotType.EquipmentMate)
            {
                item.SetFlag(ItemFlag.SoulBound);
                bound = true;
            }

            if (bound)
                itemTasks.Add(new ItemUpdateBits(item));
        }

        if (itemTasks.Count > 0)
        {
            Owner?.SendPacket(new SCItemTaskSuccessPacket(taskType, itemTasks, []));
        }
    }

    /// <summary>
    /// Removes and released all items
    /// </summary>
    public void Wipe()
    {
        while (Items.Count > 0)
        {
            RemoveItem(ItemTaskType.Invalid, Items[0], true);
        }

        UpdateFreeSlotCount();
    }

    public virtual bool CanAccept(Item item, int targetSlot)
    {
        if (item == null)
        {
            return true;
        }

        // When it's a backpack, allow only gliders by default
        if (PartOfPlayerInventory && item.Template is BackpackTemplate backpackTemplate)
        {
            return backpackTemplate.BackpackType is BackpackType.Glider or BackpackType.ToyFlag;
        }

        return true;
    }

    /// <summary>
    /// Creates a ItemContainer or descendant base of the name of the container type
    /// </summary>
    /// <param name="containerTypeName"></param>
    /// <param name="ownerId">Player Id that owns the items in this container</param>
    /// <param name="slotType"></param>
    /// <param name="createWithNewId"></param>
    /// <param name="parentUnit">Actual unit that will hold this container</param>
    /// <returns></returns>
    public static ItemContainer CreateByTypeName(string containerTypeName, uint ownerId, SlotType slotType, bool createWithNewId, Unit parentUnit)
    {
        if (containerTypeName.EndsWith("MateEquipmentContainer"))
        {
            return new MateEquipmentContainer(ownerId, slotType, createWithNewId, parentUnit);
        }

        if (containerTypeName.EndsWith("EquipmentContainer"))
        {
            return new EquipmentContainer(ownerId, slotType, createWithNewId, parentUnit);
        }

        if (containerTypeName.EndsWith("CofferContainer"))
        {
            return new CofferContainer(ownerId, createWithNewId);
        }

        if (containerTypeName.EndsWith("ItemBagContainer"))
        {
            return new ItemBagContainer(ownerId, createWithNewId);
        }

        // Fall-back
        return new ItemContainer(ownerId, slotType, createWithNewId, parentUnit);
    }

    public string ContainerTypeName()
    {
        var cName = GetType().Name;
        if (cName.Contains('.'))
        {
            cName = cName.Substring(cName.LastIndexOf('.') + 1);
        }

        return cName;
    }

    public virtual void Delete()
    {
        ItemManager.Instance.DeleteItemContainer(this);
    }

    public virtual void OnEnterContainer(Item item, ItemContainer lastContainer, byte previousSlot)
    {
        if (item is ItemBag && ItemManager.Instance.GetItemBagContainer(item.Id) is { } itemBagContainer)
            itemBagContainer.ReassignOwner(item.OwnerId);
    }

    public virtual void OnLeaveContainer(Item item, ItemContainer newContainer, byte previousSlot)
    {
        // Do Nothing
    }
}
