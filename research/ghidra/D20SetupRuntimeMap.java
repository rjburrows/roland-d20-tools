// Establish the normal C8/18/18 runtime view, preserving the entire ROM.
// Run ONLY on the Save As copy named D20-C-1.11-banked-analysis.
// This is a first mapping stage, NOT automatic bank-switch-aware analysis.
// @category RolandD20

import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.SourceType;
import java.io.ByteArrayInputStream;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20SetupRuntimeMap extends GhidraScript {
    private static final String HASH = "7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2";
    @Override
    public void run() throws Exception {
        if (currentProgram == null || !currentProgram.getDomainFile().getName().equals("D20-C-1.11-banked-analysis"))
            throw new IllegalStateException("Open the Save As copy named D20-C-1.11-banked-analysis. Original import must be retained.");
        if (!currentProgram.getLanguageID().toString().equals("z180:LE:16:default"))
            throw new IllegalStateException("Expected Z180 language.");
        Memory mem = currentProgram.getMemory();
        if (mem.getBlock("ROM_FILE_REFERENCE") != null) {
            println("Reference block already exists. No changes made; do not rerun mapping on a modified project.");
            return;
        }
        MemoryBlock original = mem.getBlock(toAddr(0));
        if (original == null || original.isOverlay() || !original.isInitialized()
                || original.getStart().getOffset() != 0 || original.getSize() != 65536)
            throw new IllegalStateException("Expected the original flat 64 KB block. No changes made.");
        byte[] rom = new byte[65536];
        if (mem.getBytes(toAddr(0), rom) != rom.length || !digest(rom).equals(HASH))
            throw new IllegalStateException("ROM checksum mismatch. No changes made.");
        int tx = currentProgram.startTransaction("D20 normal runtime map and preserved ROM");
        boolean success = false;
        try {
            monitor.checkCancelled();
            MemoryBlock reference = mem.createInitializedBlock("ROM_FILE_REFERENCE", toAddr(0),
                new ByteArrayInputStream(rom), rom.length, monitor, true);
            reference.setRead(true); reference.setWrite(false); reference.setExecute(false);
            reference.setComment("Exact original ROM file bytes. Addresses in this overlay are FILE OFFSETS, not a verified CPU mapping. Upper-half code is preserved here for later bank views.");
            mem.split(original, toAddr(0x8000));
            MemoryBlock upper = mem.getBlock(toAddr(0x8000));
            mem.removeBlock(upper, monitor);
            MemoryBlock lower = mem.getBlock(toAddr(0));
            lower.setName("ROM_NORMAL_0000_7FFF");
            lower.setRead(true); lower.setWrite(false); lower.setExecute(true);
            lower.setComment("Normal C8/18/18 view: logical 0000-7FFF -> physical 00000-07FFF. Existing disassembly remains provisional; not valid in every bank state.");
            MemoryBlock ram = mem.createUninitializedBlock("RAM_NORMAL_8000_FFFF", toAddr(0x8000), 0x8000, false);
            ram.setRead(true); ram.setWrite(true); ram.setExecute(false);
            ram.setComment("Normal C8/18/18 view: logical 8000-FFFF -> physical 20000-27FFF. RAM inferred from startup write/read tests. No hardware RAM snapshot supplied. Other CBR/BBR states are NOT represented by this block.");
            createLabel(toAddr(0x0080), "reset_startup", true, SourceType.USER_DEFINED);
            createLabel(toAddr(0x3cf6), "select_mmu_85_18_08", true, SourceType.USER_DEFINED);
            createLabel(toAddr(0x3d08), "select_mmu_C8_18_18", true, SourceType.USER_DEFINED);
            setPlateComment(toAddr(0x0080), "Reset startup. Sets SP=8100. Changes MMU repeatedly during RAM tests. This static normal view is not valid throughout startup.");
            setPlateComment(toAddr(0x015c), "Alternate mapping: CBAR=82, CBR=18, BBR=08, then JP 2000. Logical 2000 maps to physical 0A000. Association with ROM file offset A000 requires board decoding verification.");
            setPlateComment(toAddr(0x3cf6), "DI; CBAR=85, CBR=18, BBR=08; EI; RET. Logical 5000-7FFF maps to physical 0D000-0FFFF. Do not interpret calls in that window using the normal view after this routine.");
            setPlateComment(toAddr(0x3d08), "Restores normal CBAR=C8, CBR=18, BBR=18. Static RAM block represents only this bank state.");
            byte[] saved = new byte[65536];
            if (mem.getBytes(reference.getStart(), saved) != saved.length || !digest(saved).equals(HASH))
                throw new IllegalStateException("Preservation verification failed; rolling back.");
            if (mem.getBlock(toAddr(0x8000)).isInitialized())
                throw new IllegalStateException("RAM must be uninitialized; rolling back.");
            success = true;
        } finally {
            currentProgram.endTransaction(tx, success);
        }
        println("Normal runtime view created. Full ROM SHA-256 verified in ROM_FILE_REFERENCE.");
        println("This is a STATIC normal view, not a complete banking model. Automatic analysis was not requested.");
        println("Save this analysis copy, then open Window > Memory Map to inspect the blocks.");
    }
    private String digest(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
}
