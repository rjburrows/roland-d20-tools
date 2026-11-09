// Export a read-only audit of the original D-20 C 1.11 flat ROM import.
// Does not disassemble, alter memory blocks, add labels, or save the program.
// @category RolandD20

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20ExportAudit extends GhidraScript {
    @Override
    public void run() throws Exception {
        if (currentProgram == null) throw new IllegalStateException("Open the C ROM first.");
        if (!currentProgram.getLanguageID().toString().equals("z180:LE:16:default"))
            throw new IllegalStateException("Expected Z180 language; no changes made.");
        Memory memory = currentProgram.getMemory();
        byte[] rom = new byte[65536];
        if (memory.getBytes(toAddr(0), rom) != rom.length)
            throw new IllegalStateException("Expected the full flat 64 KB ROM at 0000.");
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
        if (!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
            throw new IllegalStateException("ROM bytes differ from the verified C 1.11 image. No changes made.");
        StringBuilder out = new StringBuilder();
        out.append("D-20 C 1.11 Ghidra audit\nREAD ONLY: no program modifications\n");
        out.append("Program: ").append(currentProgram.getName()).append('\n');
        out.append("Language: ").append(currentProgram.getLanguageID()).append('\n');
        out.append("ROM SHA256: ").append(hash).append('\n');
        out.append("\nMEMORY BLOCKS\n");
        for (MemoryBlock b : memory.getBlocks()) {
            out.append(String.format("%s %s..%s size=%d R=%s W=%s X=%s initialized=%s overlay=%s%n",
                b.getName(), b.getStart(), b.getEnd(), b.getSize(), b.isRead(), b.isWrite(),
                b.isExecute(), b.isInitialized(), b.isOverlay()));
        }
        out.append("\nEXISTING INSTRUCTIONS (flat-map addresses; banking not modeled)\n");
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext()) {
            monitor.checkCancelled();
            Instruction i = instructions.next();
            out.append(i.getAddress()).append("  ").append(HexFormat.of().formatHex(i.getBytes()))
                .append("  ").append(i).append('\n');
        }
        out.append("\nEXISTING FUNCTIONS\n");
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            Function f = functions.next();
            out.append(f.getEntryPoint()).append(" ").append(f.getName()).append(" ")
                .append(f.getBody()).append('\n');
        }
        out.append("\nRAW OUT0 MMU OPCODE CANDIDATES\n");
        out.append("Byte matches only: may be data, not executable instructions. Offsets are ROM file offsets.\n");
        for (int p = 0; p < rom.length - 2; p++) {
            monitor.checkCancelled();
            int reg = rom[p + 2] & 255;
            if ((rom[p] & 255) == 0xed && (rom[p+1] & 255) == 0x39 && reg >= 0x38 && reg <= 0x3a) {
                out.append(String.format("offset %04X OUT0 (%s),A; surrounding bytes: ", p,
                    new String[]{"CBR", "BBR", "CBAR"}[reg-0x38]));
                for (int q = Math.max(0,p-8); q < Math.min(rom.length,p+8); q++)
                    out.append(String.format("%02X ", rom[q] & 255));
                out.append('\n');
            }
        }
        out.append("\nEXISTING REFERENCES TO MMU IO REGISTERS\n");
        for (int reg = 0x38; reg <= 0x3a; reg++) {
            Address address = currentProgram.getAddressFactory().getAddressSpace("io").getAddress(reg);
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(address);
            while (refs.hasNext()) out.append(refs.next()).append('\n');
        }
        out.append("\nASCII RUNS (minimum 8 characters; candidates, not proven strings)\n");
        for (int p = 0; p < rom.length;) {
            int start = p;
            while (p < rom.length && (rom[p] & 255) >= 32 && (rom[p] & 255) <= 126) p++;
            if (p-start >= 8) out.append(String.format("%04X ", start))
                .append(new String(rom,start,p-start,StandardCharsets.US_ASCII)).append('\n');
            if (p == start) p++;
        }
        String[] args = getScriptArgs();
        Path folder = args.length == 1 ? Path.of(args[0]) : askDirectory("Choose folder for D-20 audit", "Choose").toPath();
        Path destination = Files.createTempFile(folder, "D20-C-audit-", ".txt");
        Files.writeString(destination, out, StandardCharsets.UTF_8);
        println("Audit exported to: " + destination.toAbsolutePath());
        println("ROM and Ghidra program unchanged.");
    }
}
