param(
    [int]$TargetProcessId = 0,
    [uint32]$QuestId = 330,
    [uint32]$StartNpcId = 3597,
    [uint32]$ReportNpcId = 11541,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

if (-not ("Aa8ReadOnlyProcessMemory" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

public sealed class Aa8ReadOnlyProcessMemory : IDisposable
{
    private const uint ProcessVmRead = 0x0010;
    private const uint ProcessQueryInformation = 0x0400;
    private IntPtr handle;

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(
        uint desiredAccess,
        bool inheritHandle,
        int processId);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadProcessMemory(
        IntPtr process,
        IntPtr address,
        byte[] buffer,
        UIntPtr size,
        out UIntPtr bytesRead);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr objectHandle);

    public Aa8ReadOnlyProcessMemory(int processId)
    {
        handle = OpenProcess(
            ProcessVmRead | ProcessQueryInformation,
            false,
            processId);
        if (handle == IntPtr.Zero)
            throw new Win32Exception(Marshal.GetLastWin32Error());
    }

    public byte[] Read(long address, int count)
    {
        byte[] buffer = new byte[count];
        UIntPtr read;
        if (!ReadProcessMemory(
                handle,
                new IntPtr(address),
                buffer,
                new UIntPtr((uint)count),
                out read) ||
            read.ToUInt64() != (ulong)count)
        {
            throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        return buffer;
    }

    public void Dispose()
    {
        if (handle != IntPtr.Zero)
        {
            CloseHandle(handle);
            handle = IntPtr.Zero;
        }
    }
}
"@
}

function Get-Aa8Process {
    if ($TargetProcessId -ne 0) {
        return Get-Process -Id $TargetProcessId
    }

    $candidates = Get-Process -Name "archeage" -ErrorAction SilentlyContinue
    foreach ($candidate in $candidates) {
        try {
            if ($candidate.Modules.ModuleName -contains "x2game.dll") {
                return $candidate
            }
        }
        catch {
            continue
        }
    }
    throw "No running ArcheAge process with x2game.dll was found."
}

function Read-Aa8Byte([long]$Address) {
    return $memory.Read($Address, 1)[0]
}

function Read-Aa8UInt32([long]$Address) {
    return [BitConverter]::ToUInt32($memory.Read($Address, 4), 0)
}

function Read-Aa8UInt64([long]$Address) {
    return [BitConverter]::ToUInt64($memory.Read($Address, 8), 0)
}

function Find-Aa8TreeNode(
    [long]$RootPointerAddress,
    [int]$NilFlagOffset,
    [uint32]$Key
) {
    $sentinel = [long](Read-Aa8UInt64 $RootPointerAddress)
    if ($sentinel -eq 0) {
        return 0L
    }

    $candidate = $sentinel
    $node = [long](Read-Aa8UInt64 ($sentinel + 8))
    $iterations = 0
    while ((Read-Aa8Byte ($node + $NilFlagOffset)) -eq 0) {
        $iterations++
        if ($iterations -gt 100000) {
            throw "AA8 tree traversal exceeded its safety limit."
        }

        $nodeKey = Read-Aa8UInt32 ($node + 0x18)
        if ($nodeKey -lt $Key) {
            $node = [long](Read-Aa8UInt64 ($node + 0x10))
        }
        else {
            $candidate = $node
            $node = [long](Read-Aa8UInt64 $node)
        }
    }

    if ($candidate -eq $sentinel) {
        return 0L
    }
    if ((Read-Aa8UInt32 ($candidate + 0x18)) -ne $Key) {
        return 0L
    }
    return $candidate
}

function Get-Aa8TreeKeys(
    [long]$RootPointerAddress,
    [int]$NilFlagOffset,
    [int]$Limit = 64
) {
    $sentinel = [long](Read-Aa8UInt64 $RootPointerAddress)
    if ($sentinel -eq 0) {
        return @()
    }

    $keys = [System.Collections.Generic.List[uint32]]::new()
    $stack = [System.Collections.Generic.Stack[long]]::new()
    $node = [long](Read-Aa8UInt64 ($sentinel + 8))
    $visited = 0

    while (($stack.Count -gt 0 -or
            (Read-Aa8Byte ($node + $NilFlagOffset)) -eq 0) -and
           $keys.Count -lt $Limit) {
        while ((Read-Aa8Byte ($node + $NilFlagOffset)) -eq 0) {
            $visited++
            if ($visited -gt 100000) {
                throw "AA8 tree enumeration exceeded its safety limit."
            }
            $stack.Push($node)
            $node = [long](Read-Aa8UInt64 $node)
        }

        if ($stack.Count -eq 0) {
            break
        }
        $node = $stack.Pop()
        $keys.Add((Read-Aa8UInt32 ($node + 0x18)))
        $node = [long](Read-Aa8UInt64 ($node + 0x10))
    }
    return $keys.ToArray()
}

$process = Get-Aa8Process
$x2game = $process.Modules |
    Where-Object { $_.ModuleName -eq "x2game.dll" } |
    Select-Object -First 1
if (-not $x2game) {
    throw "x2game.dll is not loaded in process $($process.Id)."
}

$moduleBase = $x2game.BaseAddress.ToInt64()
$memory = [Aa8ReadOnlyProcessMemory]::new($process.Id)
try {
    # Ghidra image base is 0x39000000. These are the confirmed AA8 RVAs of:
    # start NPC index, report NPC index, active journal, completed journal.
    $startRootAddress = $moduleBase + 0x03D22498
    $reportRootAddress = $moduleBase + 0x03D224B8
    $startCountAddress = $moduleBase + 0x03D224A0
    $reportCountAddress = $moduleBase + 0x03D224C0
    $activeRootAddress = $moduleBase + 0x03D22280
    $completedRootAddress = $moduleBase + 0x03D222A0

    $startNode = Find-Aa8TreeNode $startRootAddress 0x41 $StartNpcId
    $reportNode = Find-Aa8TreeNode $reportRootAddress 0x41 $ReportNpcId
    $activeNode = Find-Aa8TreeNode $activeRootAddress 0x91 $QuestId
    $completedGroup = [uint32]($QuestId -shr 6)
    $completedNode =
        Find-Aa8TreeNode $completedRootAddress 0x29 $completedGroup

    $startQuests = @()
    if ($startNode -ne 0) {
        $startQuests = @(
            Get-Aa8TreeKeys ($startNode + 0x28) 0x1D 128
        )
    }

    $reportQuests = @()
    if ($reportNode -ne 0) {
        $reportQuests = @(
            Get-Aa8TreeKeys ($reportNode + 0x28) 0x1D 128
        )
    }

    $startNpcSample = @(
        Get-Aa8TreeKeys $startRootAddress 0x41 32
    )
    $reportNpcSample = @(
        Get-Aa8TreeKeys $reportRootAddress 0x41 32
    )

    $completedMask = [uint64]0
    $isCompleted = $false
    if ($completedNode -ne 0) {
        $completedMask = Read-Aa8UInt64 ($completedNode + 0x20)
        $bit = [int]($QuestId -band 0x3F)
        $isCompleted = ($completedMask -band ([uint64]1 -shl $bit)) -ne 0
    }

    $result = [ordered]@{
        authority = "x2game.dll Kakao 8.0.3.12 r558734 live memory"
        read_only = $true
        process = [ordered]@{
            id = $process.Id
            name = $process.ProcessName
            x2game_base = ("0x{0:X16}" -f $moduleBase)
        }
        quest = [ordered]@{
            id = $QuestId
            active_entry_found = $activeNode -ne 0
            active_status = if ($activeNode -ne 0) {
                Read-Aa8UInt32 ($activeNode + 0x2C)
            }
            else {
                $null
            }
            completed_group = $completedGroup
            completed_group_found = $completedNode -ne 0
            completed_mask = ("0x{0:X16}" -f $completedMask)
            completed = $isCompleted
        }
        npc_indexes = [ordered]@{
            start_entry_count = Read-Aa8UInt64 $startCountAddress
            start_npc_sample = $startNpcSample
            start_npc = $StartNpcId
            start_entry_found = $startNode -ne 0
            start_quests = $startQuests
            start_contains_quest = $startQuests -contains $QuestId
            report_entry_count = Read-Aa8UInt64 $reportCountAddress
            report_npc_sample = $reportNpcSample
            report_npc = $ReportNpcId
            report_entry_found = $reportNode -ne 0
            report_quests = $reportQuests
            report_contains_quest = $reportQuests -contains $QuestId
        }
    }

    $json = $result | ConvertTo-Json -Depth 8
    $json
    if ($OutputPath) {
        $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
        [System.IO.File]::WriteAllText(
            $resolvedOutput,
            $json + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false))
    }
}
finally {
    $memory.Dispose()
}
