// Trace the preset ROM selector, editor import, bank register, and display names.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceABFactoryPatterns extends GhidraScript {
    public void run() throws Exception {
        if (!currentProgram.getLanguageID().toString().equals("MCS96:LE:16:default"))
            throw new IllegalStateException("Expected Intel MCS-96 language");
        Memory memory = currentProgram.getMemory();
        MemoryBlock block = memory.getBlock(currentProgram.getMinAddress());
        if (block == null || block.getSize() != 65536)
            throw new IllegalStateException("Expected the 64 KiB interleaved A/B image");
        byte[] rom = new byte[65536];
        memory.getBytes(block.getStart(), rom);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
        if (!hash.equals("283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca"))
            throw new IllegalStateException("Unexpected A/B ROM " + hash);
        StringBuilder out = new StringBuilder("A/B 1.12 SHA256 " + hash + "\n"
            + "Program file offsets treated as CPU addresses provisionally.\n"
            + "Banked CPU B000 is distinct from flat program ROM file B000.\n");
        AddressSet region = new AddressSet(block.getStart(), block.getEnd());
        // Repair two stale boundaries in the transient research analysis only.
        // 11FE B0 ED F5 is one LDB instruction; 1A1F 26 F7 is one SJMP.
        clearListing(block.getStart().add(0x11fe), block.getStart().add(0x1200));
        clearListing(block.getStart().add(0x1a1f), block.getStart().add(0x1a6c));
        for (int seed : new int[]{0x11fe,0x1a1f,0x1a21}) {
            DisassembleCommand repair = new DisassembleCommand(block.getStart().add(seed), region, true);
            repair.enableCodeAnalysis(false);
            repair.applyTo(currentProgram, monitor);
        }
        int[][] spans = {{0x11d0,0x122f},{0x16ed,0x173b},{0x19d1,0x1a6c},{0x1a21,0x1a6c},
            {0x1a6d,0x1ae0},{0x1ceb,0x1d07},{0x42b0,0x4330},{0x5e70,0x5ec0}};
        for (int[] span : spans) {
            Address start = block.getStart().add(span[0]);
            Address end = block.getStart().add(span[1]);
            DisassembleCommand command = new DisassembleCommand(start, region, true);
            command.enableCodeAnalysis(false);
            command.applyTo(currentProgram, monitor);
            out.append(String.format("\n[%04X-%04X] seeds require caller verification\n", span[0], span[1]));
            for (InstructionIterator it = currentProgram.getListing().getInstructions(new AddressSet(start,end),true); it.hasNext();) {
                Instruction ins = it.next();
                out.append(ins.getAddress()).append(' ')
                   .append(HexFormat.of().formatHex(ins.getBytes())).append(' ')
                   .append(ins).append('\n');
            }
        }
        out.append("\nPreset display labels at flat program ROM AF1A, 11 bytes each:\n");
        for (int i = 0; i < 32; i++) {
            out.append(String.format("%02X ", i))
               .append(new String(rom,0xaf1a + 11*i,11,java.nio.charset.StandardCharsets.US_ASCII))
               .append('\n');
        }
        out.append("\nDiscovered references:\n");
        for (int target : new int[]{0x11e0,0x16ed,0x19d1,0x1a6d,0x1ceb,0x42b0,0x5e70,0xaf1a,0xb000}) {
            out.append(String.format("%04X:",target));
            for (Reference ref : currentProgram.getReferenceManager().getReferencesTo(block.getStart().add(target)))
                out.append(' ').append(ref.getFromAddress()).append(' ').append(ref.getReferenceType());
            out.append('\n');
        }
        Files.writeString(Path.of(getScriptArgs()[0]),out);
        println("Exported factory pattern evidence to " + getScriptArgs()[0]);
    }
}
