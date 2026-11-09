// Reconstruct indirect disk load callback dispatch, without asserting file/RAM meaning.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceDiskLoadCallbacks extends GhidraScript {
 public void run() throws Exception {
  Memory memory=currentProgram.getMemory();
  MemoryBlock raw=memory.getBlock("ROM_FILE_REFERENCE");
  MemoryBlock bank=memory.getBlock("CANDIDATE_85_18_08");
  if(raw==null||raw.getSize()!=65536||bank==null||bank.getSize()!=0x3000)
   throw new IllegalStateException("Expected mapped C 1.11 research copy");
  byte[] rom=new byte[65536];memory.getBytes(raw.getStart(),rom);
  String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if(!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))
   throw new IllegalStateException("Unexpected C ROM: "+hash);
  AddressSet region=new AddressSet(bank.getStart(),bank.getEnd());
  StringBuilder out=new StringBuilder("C 1.11 ROM SHA256 "+hash+"\n"
   +"Candidate bank 85/18/08; logical 5000-7FFF = file D000-FFFF.\n"
   +"Disassembly of indirect callbacks; static paths only.\n\n"
   +"16 callback words at logical 615A:\n");
  for(int i=0;i<16;i++){
   int offset=0xe15a+2*i;
   int target=(rom[offset]&255)|((rom[offset+1]&255)<<8);
   out.append(String.format("slot %02d -> %04X\n",i+1,target));
   if(target>=0x5000&&target<0x8000){
    DisassembleCommand command=new DisassembleCommand(bank.getStart().add(target-0x5000),region,true);
    command.enableCodeAnalysis(false);command.applyTo(currentProgram,monitor);
   }
  }
  out.append("\nClass dispatch bytes at logical 5807-5813 (ROM D807-D813): ");
  for(int a=0xd807;a<=0xd813;a++)out.append(String.format("%02X ",rom[a]&255));
  out.append("\nDisk signature at logical 64F4: ");
  for(int a=0xe4f4;a<0xe4f4+13;a++)out.append((char)(rom[a]&255));
  out.append("\n");
  for(int seed:new int[]{0x58c3,0x59b1,0x5a5e,0x5cda,0x5d5d,0x5ded,0x5e14,0x5f16}){
   DisassembleCommand command=new DisassembleCommand(bank.getStart().add(seed-0x5000),region,true);
   command.enableCodeAnalysis(false);command.applyTo(currentProgram,monitor);
  }
  for(int[] span:new int[][]{{0x58c3,0x5d2e},{0x5d5d,0x5e1f},{0x615a,0x6179},
    {0x5e14,0x5e48},{0x5f16,0x5f80},{0x6650,0x66e0},
    {0x6710,0x67ff},{0x6870,0x68cf}}){
   out.append(String.format("\n[%04X-%04X]\n",span[0],span[1]));
   Address start=bank.getStart().add(span[0]-0x5000);
   Address end=bank.getStart().add(span[1]-0x5000);
   for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);it.hasNext();){
    Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(ins).append('\n');
   }
  }
  Files.writeString(Path.of(getScriptArgs()[0]),out);
  println("Exported "+getScriptArgs()[0]);
 }
}
