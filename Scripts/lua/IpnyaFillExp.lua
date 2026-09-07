-- Custom r575 planner and single-cast request encoder. No inventory writes or new native bindings.
local B = {}
local function number(v) return tonumber(v) or 0 end
local function key(items, scale)
    local parts = {}
    for _, v in ipairs(items) do
        if number(v.count) ~= scale then return nil end
        parts[#parts + 1] = tostring(v.item.itemType)
    end
    table.sort(parts)
    return table.concat(parts, ":")
end

function B.Families(info)
    local families, seen = {}, {}
    for _, r in ipairs(info) do
        local k = key(r.itemList, 1)
        local gain, cost = number(r.gainExp), number(r.currencyValue)
        if k and #r.itemList > 0 and #r.itemList <= 2 and gain >= 45 and
            gain <= 175 and cost >= 0 and number(r.currency) == 0 and not seen[k] then
            local f = { key = k, one = r, gain = gain, cost = cost }
            seen[k] = f
            families[#families + 1] = f
        end
    end
    if #families > 4 then return {} end -- Bound the exhaustive r575 search.
    for _, r in ipairs(info) do
        local f = seen[key(r.itemList, 5)]
        if f and number(r.gainExp) == 5 * f.gain and
            number(r.currencyValue) == 5 * f.cost and number(r.currency) == 0 then
            f.five = r
        end
    end
    table.sort(families, function(a, b)
        if a.gain ~= b.gain then return a.gain > b.gain end
        return a.key < b.key
    end)
    return families
end

-- Enumerate bounded integer recipes with shared inventory, including essence.
-- The last family needs only ceil(remaining/gain); extra copies cannot improve
-- the lexicographic objective: overflow, gold, item count, casting count.
function B.Plan(info, bag, mode, families)
    local need = number(info.totalExp) - number(info.curExp)
    if need <= 0 or need > 3900 then return nil end
    families = families or B.Families(info)
    local fs = {}
    for _, f in ipairs(families) do
        if mode == "mixed" or mode == f.key then fs[#fs + 1] = f end
    end
    if #fs == 0 then return nil end
    local stock, chosen, best = {}, {}, nil
    for _, f in ipairs(fs) do
        for _, v in ipairs(f.one.itemList) do stock[v.item.itemType] = number(bag(v.item.itemType)) end
    end
    local function search(i, exp, gold, items, casts)
        if exp >= need then
            if not best or exp < best.exp or (exp == best.exp and
                (gold < best.gold or (gold == best.gold and
                (items < best.items or (items == best.items and casts < best.casts))))) then
                best = { exp = exp, gold = gold, items = items, casts = casts, counts = {} }
                for j = 1, #fs do best.counts[j] = chosen[j] or 0 end
            end
            return
        end
        local f = fs[i]
        if not f then return end
        local limit = math.ceil((need - exp) / f.gain)
        for _, v in ipairs(f.one.itemList) do limit = math.min(limit, stock[v.item.itemType]) end
        local first = i == #fs and math.ceil((need - exp) / f.gain) or 0
        for n = first, limit do
            chosen[i] = n
            for _, v in ipairs(f.one.itemList) do stock[v.item.itemType] = stock[v.item.itemType] - n end
            local count = f.five and (math.floor(n / 5) + n % 5) or n
            search(i + 1, exp + n * f.gain, gold + n * f.cost, items + n * #f.one.itemList, casts + count)
            for _, v in ipairs(f.one.itemList) do stock[v.item.itemType] = stock[v.item.itemType] + n end
        end
        chosen[i] = nil
    end
    search(1, 0, 0, 0, 0)
    if not best then return nil end
    local plan = { mode = mode, startExp = number(info.curExp), totalExp = number(info.totalExp),
        gainExp = best.exp, overflow = best.exp - need, currencyValue = best.gold,
        currency = 0, itemList = {}, steps = {} }
    local totals = {}
    for i, f in ipairs(fs) do
        local n = best.counts[i]
        for _, v in ipairs(f.one.itemList) do
            local id = v.item.itemType
            if n > 0 then
                if not totals[id] then
                    totals[id] = { item = v.item, count = 0 }
                    plan.itemList[#plan.itemList + 1] = totals[id]
                end
                totals[id].count = totals[id].count + n
            end
        end
        while n > 0 do
            local step = f.five and n >= 5 and f.five or f.one
            plan.steps[#plan.steps + 1] = step
            n = n - (step == f.five and 5 or 1)
        end
    end
    table.sort(plan.itemList, function(a, b) return a.item.itemType < b.item.itemType end)
    local parts = { mode, tostring(plan.startExp), tostring(plan.totalExp), tostring(best.exp), tostring(best.gold) }
    for _, v in ipairs(plan.itemList) do parts[#parts + 1] = tostring(v.item.itemType) .. "=" .. tostring(v.count) end
    for _, r in ipairs(plan.steps) do parts[#parts + 1] = tostring(r.materialType) end
    plan.signature = table.concat(parts, ";")
    return plan
end

function B.Options(info, bag)
    local fs, result = B.Families(info), {}
    local function add(mode, name)
        local p = B.Plan(info, bag, mode, fs)
        if p then
            p.name = "Completar EXP: " .. name
            p.batchPlan = p
            result[#result + 1] = p
        end
    end
    add("mixed", "combinación disponible")
    for _, f in ipairs(fs) do add(f.key, f.one.name) end
    return result
end

-- One custom request; recipe multipliers describe one aggregate payment.
local nextRequestId = 0
function B.Request(plan, slot, level)
    nextRequestId = nextRequestId % 2147483647 + 1
    local counts, ids = {}, {}
    for _, recipe in ipairs(plan.steps) do
        local id = recipe.materialType
        if not counts[id] then counts[id] = 0; ids[#ids + 1] = id end
        counts[id] = counts[id] + 1
    end
    table.sort(ids)
    local parts = {string.format("%d,%d,%d,%d,%d,%d", nextRequestId, slot - 1, level,
        plan.startExp, plan.gainExp, plan.currencyValue)}
    for _, id in ipairs(ids) do parts[#parts + 1] = string.format("%d:%d", id, counts[id]) end
    local command = table.concat(parts, "/")
    if #command > 233 then return nil end
    return command, nextRequestId
end

-- r575 JoinUserChatChannel copies at most 48 name bytes. Reserved names are
-- intercepted by our backend and never become channels or player messages.
function B.Frames(payload, requestId)
    local count = math.ceil(#payload / 23)
    local frames = {}
    for index = 1, count do
        frames[index] = string.format("aa10ip3:%d:%d:%d:%s", requestId, index, count,
            string.sub(payload, (index - 1) * 23 + 1, index * 23))
        if #frames[index] > 48 then return nil end
    end
    return frames
end
function B.Send(payload, requestId)
    local frames = B.Frames(payload, requestId)
    if not frames then return false end
    for _, frame in ipairs(frames) do X2Chat:JoinUserChatChannel(frame, "") end
    return true
end
function B.Cancel(requestId)
    X2Chat:JoinUserChatChannel("aa10ip3cancel:" .. tostring(requestId), "")
end

-- Observes one cast. Never sends, retries or queues another request.
function B.Watch(plan, level)
    local q = { elapsed = 0, quiet = 0 }
    function q:Tick(dt, info, working, visible)
        if self.stopped then return "stopped" end
        dt = math.max(0, number(dt)); self.elapsed = self.elapsed + dt
        if not visible or not info or info.level ~= level or number(info.totalExp) ~= plan.totalExp then
            self.stopped = true; return "stopped"
        end
        local exp = number(info.exp)
        if exp == plan.totalExp and not working then self.stopped = true; return "done" end
        if working then self.sawCast = true; self.quiet = 0
        elseif self.sawCast then self.quiet = self.quiet + dt end
        if (exp ~= plan.startExp and exp ~= plan.totalExp) or self.quiet > 1500 or
            (not self.sawCast and self.elapsed > 10000) or self.elapsed > 60000 then
            self.stopped = true; return "stopped"
        end
        return "waiting"
    end
    return q
end
return B
