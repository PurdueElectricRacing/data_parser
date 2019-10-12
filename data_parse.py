import csv
import json
import os
from tkinter import filedialog
import tkinter
import ctypes

def remove_duplicates(data):
  seen = set()
  ret = list()
  for value in data:
    if value not in seen:
      seen.add(value)
      ret.append(value)
  
  return ret

def group_bytes(bytes: str):
  # print("raw values:", bytes)
  grouped_bytes: int = list()

  i = 0;
  data = ""
  # split data into an array of integers based on bytes (i.e. 2 consecutive numbers in the data string)
  while i < len(bytes):
    # append character to data string
    data += bytes[i]
    i += 1

    if (i % 2) == 0:
      value = 0
      try:
        value = int(data, 16)
      except Exception as e:
        print(e, "value =", data)
        value = 0
      grouped_bytes.append(value)
      data = ""

  return grouped_bytes

def parseEntry(timestamp, entry, filemaps):
 
  # data comes in in form <address>,<data>
  value = entry.split(",")
  address = value[0]
  data = value[1]
  convertedValues = list()
  
  # filemap format: <address> : (bytes[], file_pointer)
  bytes = filemaps[address][0]
  fp = filemaps[address][1]
  # 0028090ABBEFFFE -> [00, 28, 9, A, BB, EF, FF, FE] except in base 10 lol
  split_bytes = group_bytes(data); 
  # print(split_bytes)
  
  previousByte = None
  previousValue = split_bytes[0]

  i = 0


  for byteName in bytes:
    if not byteName:
      i += 1
      continue

    if i == len(split_bytes):
      break

    # if previous byte name is same as current one, left shift and OR data
    if previousByte == byteName:
      previousValue = previousValue << 8
      previousValue |= split_bytes[i]
      # print(previousValue)
    else:
      if i > 0:
        convertedValues.append(previousValue)
      previousValue = split_bytes[i]
    
    previousByte = byteName
    i += 1
  # end for
  convertedValues.append(previousValue)
    # exit()
  
  i = 0
  scalar = 1
  while i < len(convertedValues):
    # exit()
    # coolant flow speed / wheel speed
    if address == "721" or address == "700" or address == "701":
      scalar = 1
    # motor coolant
    elif address == "720":
      scalar = 1 / 100.0
    # IMU data, 0 = accelerometer, 1 = gyro 
    elif address == "421":
     
      if convertedValues[0] == 0:
        convertedValues[0] = 'Accelerometer'
        scalar = (0.122 / 1000)
      else:
        convertedValues[0] = 'Gyroscope'
        scalar = (8.75 / 1000)
      i += 1
    # pedalbox data not sure what's happening here
    elif address == '501':
      index = len(convertedValues - 1)
      val = ctypes.c_int32(convertedValues[index])
      convertedValues[index] = val;
    # torque command to MC
    elif address == '0C0':
      index = len(convertedValues - 1)
      val = ctypes.c_int32(convertedValues[index])
      convertedValues[index] = val;
      scaler = 1 / 100.0

    convertedValues[i] = float(convertedValues[i]) * scalar;
    i += 1


  # print(convertedValues)
    
  if address == '0AC':
    print (convertedValues);
  convertedValues.insert(0, timestamp)
  mapped_values = {address : convertedValues}
  return mapped_values

def dumpData(data, file_pointers):
  # rows is a list of format {address : data values[]}
  # lots of repetition in the data storage but idc man i do what i want
  # this isnt kept running, it's just once through.
  for row in data:
    # will be a list of length 1, hence why can do first index
    address = list(row.keys())[0]
    datas = row[address]
    file_pointer = file_pointers[address][1]
    # print(address, datas)
    file_pointer.writerow(datas)


if __name__ == "__main__":
  print("input data file name")
  root = tkinter.Tk()
  root.withdraw()

  data_file = tkinter.filedialog.askopenfilename(title="Select Data File", filetypes =(("Text File", "*.txt"),("All Files","*.*")));
  if not data_file:
    exit()
  # open the json containing the addresses and byte mappings 
  DAQ_fp = open("DAQ.json");
  if not DAQ_fp:
    print("error opening DAQ.json")
    exit(-1)

  json_reader = json.load(DAQ_fp);
  # list of addresses mapped to a list of their data bytes
  address_maps = json_reader["addresses"];
  # address : [bytes[], filepointer]
  outfiles = dict();
  # strip off file extension
  newdir = data_file.split(".")[0]

  try:
    os.mkdir(newdir)
  except Exception as e:
    print(e)

  for address in address_maps:
    byteList = address["bytes"]
    # headers list (timestamp, data1 name, ... dataN name)
    headers = list(byteList)
    # remove duplicate byte entries
    headers = remove_duplicates(headers)

    filename = newdir + "\\"
    addr = address["address"]
    # loop through bytes in address list, because i am too laxzy to figure out clever names for each of the addresses
    for header in headers:
      filename += header + "_"
    # output to a csv
    filename += ".csv"
    
    headers.insert(0, "timestamp")

    fp = open(filename, "a")
    output = csv.writer(fp, lineterminator='\n')
    # write the headers to the output csv
    output.writerow(headers)
    # print(headers)

    # map the address to a file pointer
    bytesFP = (byteList, output)

    outfiles[addr] = bytesFP
  # exit(0)
  # open data file
  with open(data_file, "r") as fp:
    line: str = fp.readline();
    rows = list()
    # for every line in the file
    while line:
      data = line.split(";");
      # timestamp is first value in the line
      timestamp = data[0];
      i = 1; 

      # parse every data entry in a line
      while i < len(data):
        parsedData = parseEntry(timestamp, data[i], outfiles)
        rows.append(parsedData)
        i += 1
        # print(parsedData)
      line = fp.readline();

      if len(rows) == 256:
        dumpData(data=rows, file_pointers=outfiles)
        rows.clear()
    # print(rows)
    # exit(1)
    dumpData(data=rows, file_pointers=outfiles)
    print ('Dumping complete. Don\'t forget to flush.')
   

