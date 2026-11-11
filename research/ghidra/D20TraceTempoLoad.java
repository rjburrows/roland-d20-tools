// Trace the first native header/data transfer and direct tempo operands.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceTempoLoad extends GhidraScript {
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        MemoryBlock reference = memory.getBlock("ROM_FILE_REFERENCE");
        MemoryBlock normal = memory.getBlock("ROM_NORMAL_0000_7FFF");
        MemoryBlock disk = memory.getBlock("CANDIDATE_85_18_08");
        if (reference == null || normal == null || disk == null || reference.getSize() != 65536)
            throw new IllegalStateException("Expected the mapped C 1.11 research copy");
        byte[] rom = new byte[65536];
        memory.getBytes(reference.getStart(), rom);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
        if (!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
            throw new IllegalStateException("Unexpected ROM " + hash);
        StringBuilder out = new StringBuilder("C 1.11 SHA256 " + hash
            + "\nStatic normal and candidate disk-bank instruction evidence\n");
        int[][] normalSpans = {
            {0,0x7f}, {0x0014,0x0017}, {0x0018,0x001b}, {0x180,0x1a0}, {0x3cb0,0x3d60},
            {0x418a,0x41c8}, {0x41be,0x41d0}, {0x7654,0x76cc}
        };
        for (int[] span : normalSpans) export(normal, 0, span[0], span[1], out);
        int[][] diskSpans = {
            {0x5000,0x5075}, {0x51ca,0x5270}, {0x5807,0x5872},
            {0x5a5e,0x5c29}, {0x5cb0,0x5ceb}, {0x5e14,0x5e5a},
            {0x603d,0x6075}, {0x6129,0x6179}, {0x6653,0x66c4}, {0x6658,0x66ba},
            {0x6593,0x65da}, {0x65db,0x6652}, {0x6a6e,0x6b3f}, {0x655b,0x6592},
            {0x6721,0x6784}, {0x6f1c,0x6f35}, {0x73dd,0x743e}
        };
        for (int[] span : diskSpans) export(disk, 0x5000, span[0], span[1], out);
        out.append("\nRaw vectors 0000-007F:\n");
        for (int i = 0; i < 128; i++)
            out.append(String.format("%02X%s", rom[i] & 255, i % 16 == 15 ? "\n" : " "));
        out.append("\nRaw D0 B4 operands in normal ROM (possible code or data):\n");
        for (int i = 0; i < 0x7fff; i++) {
            if ((rom[i] & 255) == 0xd0 && (rom[i + 1] & 255) == 0xb4)
                out.append(String.format("operand file %04X\n", i));
        }
        Files.writeString(Path.of(getScriptArgs()[0]), out);
        println("Exported tempo load evidence to " + getScriptArgs()[0]);
    }

    private void export(MemoryBlock block, int base, int first, int last,
                        StringBuilder out) throws Exception {
        Address start = block.getStart().add(first - base);
        Address end = block.getStart().add(last - base);
        AddressSet region = new AddressSet(block.getStart(), block.getEnd());
        DisassembleCommand command = new DisassembleCommand(start, region, true);
        command.enableCodeAnalysis(false);
        command.applyTo(currentProgram, monitor);
        out.append(String.format("\n[%s %04X-%04X]\n", block.getName(), first, last));
        for (InstructionIterator it = currentProgram.getListing().getInstructions(
                new AddressSet(start, end), true); it.hasNext();) {
            Instruction instruction = it.next();
            out.append(instruction.getAddress()).append(' ').append(instruction).append('\n');
        }
    }
}
