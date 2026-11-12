// Hash-checked recording input producers and edit/copy evidence.
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

public class D20TraceSongInputs extends GhidraScript {
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
        byte[] mapped = new byte[32768];
        memory.getBytes(normal.getStart(), mapped);
        if (!java.util.Arrays.equals(mapped, java.util.Arrays.copyOf(rom,32768)))
            throw new IllegalStateException("Normal view differs from checked reference ROM");
        StringBuilder out = new StringBuilder("C 1.11 SHA256 " + hash
            + "\nNormal C8/18/18. Static branches are not proof of active runtime mode.\n");
        int[][] spans = {{0x0400,0x0640},{0x079e,0x09b0},{0x0c00,0x1005},{0x1006,0x11bf},{0x11c0,0x144d},{0x14b1,0x1728},{0x1400,0x14b0},
            {0x1700,0x19d1},{0x44c0,0x4520},{0x7b00,0x7ec0}};
        AddressSet region = new AddressSet(normal.getStart(), normal.getEnd());
        // Seed only decoded call targets or verified instruction boundaries.
        for (int seed : new int[]{0x0404,0x079e,0x0870,0x0904,0x08e8,0x0970,0x0547,0x11db,0x12b3,0x137c,0x138f,0x13a4,0x14b1,0x14ce,0x1565,0x158b,0x0d20,0x0de1,0x0de6,0x0df4,0x0e02,0x0e9e,0x0ebc,0x11c0,0x1006,0x101e,0x1045,0x107c,0x10df,0x1151,0x1181,
                0x144e,0x1893,0x189b,0x1729,0x172e,0x44c8,
                0x7b55,0x7b7a,0x7b90,0x7bbd,0x7c10,0x7c3a,0x7c7a,
                0x7cb8,0x7cc6,0x7d2b,0x7d3f,0x7d6a,0x7d90,0x7dae,0x7dcc,0x7e38,0x7e80}) {
            DisassembleCommand command = new DisassembleCommand(normal.getStart().add(seed), region, true);
            command.enableCodeAnalysis(false);
            command.applyTo(currentProgram, monitor);
        }
        for (int[] span : spans) {
            Address first = normal.getStart().add(span[0]);
            out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
            for (InstructionIterator it = currentProgram.getListing().getInstructions(
                    new AddressSet(first, normal.getStart().add(span[1])), true); it.hasNext();) {
                Instruction ins = it.next();
                out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes()))
                    .append(' ').append(ins).append('\n');
            }
        }
        for (int table : new int[]{0x0db9,0x1232}) {
            out.append(String.format("\nChannel dispatch table %04X (8x through Fx):\n",table));
            for (int i=0;i<8;i++) {
                int at=table+2*i;
                int target=(rom[at]&255)|((rom[at+1]&255)<<8);
                out.append(String.format("%Xx -> %04X\n",i+8,target));
            }
        }
        out.append("\nRaw direct operands / possible code or data; normal half only:\n");
        for (int target : new int[]{0xb47e,0xb47f,0xb480,0xb486,0xb489,0x65c0}) {
            out.append(String.format("target %04X:",target));
            for (int i=0;i<0x7fff;i++)
                if ((rom[i]&255)==(target&255) && (rom[i+1]&255)==(target>>8))
                    out.append(String.format(" %04X",i));
            out.append('\n');
        }
        Files.writeString(Path.of(getScriptArgs()[0]),out);
        println("Exported recording input evidence to " + getScriptArgs()[0]);
    }
}
