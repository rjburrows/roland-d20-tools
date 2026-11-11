// Hash-checked static evidence for lane remapping and MIDI output dispatch.
// Run on the mapped C 1.11 copy with analyzeHeadless -readOnly -noanalysis.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceSongRouting extends GhidraScript {
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        MemoryBlock reference = memory.getBlock("ROM_FILE_REFERENCE");
        MemoryBlock normal = memory.getBlock("ROM_NORMAL_0000_7FFF");
        if (reference == null || normal == null || reference.getSize() != 65536)
            throw new IllegalStateException("Expected mapped C 1.11 research copy");
        byte[] rom = new byte[65536];
        memory.getBytes(reference.getStart(), rom);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
        if (!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
            throw new IllegalStateException("Unexpected C ROM " + hash);
        StringBuilder out = new StringBuilder("C 1.11 SHA256 " + hash
            + "\nNormal C8/18/18. Static branches are not proof of active runtime mode.\n");
        int[][] spans = {{0x0404,0x0442},{0x1b38,0x1b8a},{0x19d2,0x19ff},
            {0x3565,0x35a6},{0x4533,0x4548},{0x4a10,0x4a78},
            {0x12e1,0x1308},{0x12f7,0x1308},{0x5a9f,0x5ad5},
            {0x66e5,0x6731},{0x69ac,0x6a16},{0x492b,0x4a1b},
            {0x48ff,0x492a},{0x2d36,0x2d7b},{0x431c,0x433b},
            {0x08ad,0x08e7},{0x0935,0x0970},{0x17c0,0x17f0},
            {0x45b2,0x45ef},
            {0x1820,0x1870},
            {0x4870,0x48fe},
            {0x6a81,0x6b50},{0x6d55,0x6eab},{0x6e51,0x6eab},
            {0x6e88,0x6eab},{0x6f6a,0x6fdb},
            {0x6fdc,0x7097},{0x7098,0x70b0},{0x7294,0x7398},{0x74a5,0x75a0},
            {0x7764,0x7860},{0x1e00,0x1ea0},{0x62d0,0x6340},{0x75a1,0x75e8}};
        AddressSet region = new AddressSet(normal.getStart(), normal.getEnd());
        for (int[] span : spans) {
            Address first = normal.getStart().add(span[0]);
            DisassembleCommand command = new DisassembleCommand(first, region, true);
            command.enableCodeAnalysis(false);
            command.applyTo(currentProgram, monitor);
            out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
            for (InstructionIterator it = currentProgram.getListing().getInstructions(
                    new AddressSet(first, normal.getStart().add(span[1])), true); it.hasNext();) {
                Instruction ins = it.next();
                out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes()))
                    .append(' ').append(ins).append('\n');
            }
        }
        out.append("\nRaw direct operands / possible code or data; normal half only:\n");
        for (int target : new int[]{0xb448,0xb44f,0xb450,0xb4cf,0xb4d1,0x69ea,0x6e19,0x7294}) {
            out.append(String.format("target %04X:",target));
            for (int i=0;i<0x7fff;i++)
                if ((rom[i]&255)==(target&255) && (rom[i+1]&255)==(target>>8))
                    out.append(String.format(" %04X",i));
            out.append('\n');
        }
        Files.writeString(Path.of(getScriptArgs()[0]),out);
        println("Exported routing evidence to " + getScriptArgs()[0]);
    }
}
