// Trace native section selection and initial-state candidates without guessing fields.
// @category RolandD20
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.io.ByteArrayInputStream;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;

public class D20TraceSavedInitialState extends GhidraScript {
 public void run() throws Exception {
  Memory memory=currentProgram.getMemory();
  MemoryBlock raw=memory.getBlock("ROM_FILE_REFERENCE"),normal=memory.getBlock("ROM_NORMAL_0000_7FFF");
  if(raw==null||normal==null||raw.getSize()!=65536)throw new IllegalStateException("Mapped C copy required");
  byte[] rom=new byte[65536];memory.getBytes(raw.getStart(),rom);
  String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rom));
  if(!hash.equals("7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2"))throw new IllegalStateException("Unexpected ROM");
  MemoryBlock disk=memory.getBlock("CANDIDATE_85_18_08");
  if(disk==null)disk=memory.createInitializedBlock("CANDIDATE_85_18_08",toAddr(0x5000),new ByteArrayInputStream(rom,0xd000,0x3000),0x3000,monitor,true);
  disk.setRead(true);disk.setWrite(false);disk.setExecute(true);
  StringBuilder out=new StringBuilder("C1.11 SHA256 "+hash+"\nNormal C8/18/18; disk 85/18/08 maps logical5000 to fileD000. Static flow, no runtime RAM snapshot.\n");
  for(int[] s:new int[][]{{0x51ca,0x5235},{0x553f,0x558e},{0x558f,0x55dc},
     {0x55dd,0x56d1},{0x56d2,0x5773},
     {0x5786,0x5872},{0x5a5e,0x5cd9},{0x5cda,0x5d1f},{0x5d20,0x5d5c},
     {0x5d5d,0x5dec},{0x5ded,0x5e5a},
     {0x5e49,0x5e5a}})export(disk,0x5000,s[0],s[1],out);
  for(int[] s:new int[][]{{0x3d99,0x3db4},{0x4cef,0x4d3c},{0x65a0,0x65d0},
     {0x780a,0x788c},{0x55ad,0x55b6}})
    export(normal,0,s[0],s[1],out);
  out.append("\nDispatch lists / separators at disk5807..5813:\n");
  for(int a=0xd807;a<=0xd813;a++)out.append(String.format("%04X %02X\n",a-0x8000,rom[a]&255));
  out.append("\nRaw operands in normal half (code/data candidates):\n");
  for(int t=0xb4ba;t<=0xb4cf;t++)scan(rom,t,out);
  for(int t:new int[]{0xb448,0xb450,0xb715,0xb716,0xb717,0xb718,0xb719,0xb71a,0xb71b,0xb71c})scan(rom,t,out);
  Files.writeString(Path.of(getScriptArgs()[0]),out);
 }
 private void scan(byte[] rom,int t,StringBuilder out){out.append(String.format("%04X:",t));for(int i=0;i<0x7fff;i++)if((rom[i]&255)==(t&255)&&(rom[i+1]&255)==(t>>8))out.append(String.format(" %04X",i));out.append('\n');}
 private void export(MemoryBlock b,int base,int first,int last,StringBuilder out)throws Exception {
  Address start=b.getStart().add(first-base),end=b.getStart().add(last-base);
  DisassembleCommand cmd=new DisassembleCommand(start,new AddressSet(b.getStart(),b.getEnd()),true);
  cmd.enableCodeAnalysis(false);cmd.applyTo(currentProgram,monitor);
  out.append(String.format("\n[%s %04X-%04X]\n",b.getName(),first,last));
  for(InstructionIterator it=currentProgram.getListing().getInstructions(new AddressSet(start,end),true);it.hasNext();){Instruction ins=it.next();out.append(ins.getAddress()).append(' ').append(HexFormat.of().formatHex(ins.getBytes())).append(' ').append(ins).append('\n');}
 }
}
