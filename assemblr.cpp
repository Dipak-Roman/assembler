#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

// Convert string to uppercase
string toUpper(string str) {
  transform(str.begin(), str.end(), str.begin(),
    [](unsigned char c) { return toupper(c); });

  return str;
}

// Remove spaces from beginning and end
string trim(string str) {
  size_t start = str.find_first_not_of(" \t");

  if (start == string::npos)
    return "";

  size_t end = str.find_last_not_of(" \t");

  return str.substr(start, end - start + 1);
}

// Check whether mnemonic exists
bool mnemonicExists(const vector<string> &opcodeTable, const string &mnemonic) {
  for (const string &item : opcodeTable) {
    if (item == mnemonic)
      return true;
  }

  return false;
}

// Identify operand type
string getOperandType(string operand) {
  operand = trim(operand);

  string upperOperand = toUpper(operand);

  // REGISTER

  vector<string> registers = {
    "EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "ESP", "EBP"
  };

  for (const string &reg : registers) {
    if (upperOperand == reg)
      return "Register";
  }

  // MEMORY
  if (operand.front() == '[' && operand.back() == ']') {
    return "Memory";
  }

  // CONSTANT
  bool isNumber = true;

  int start = 0;

  if (operand[0] == '-' || operand[0] == '+')
    start = 1;

  for (int i = start; i < operand.length(); i++) {
    if (!isdigit(operand[i])) {
      isNumber = false;
      break;
    }
  }

  if (isNumber && operand.length() > start)
    return "Constant";

  // SYMBOL
  return "Symbol";
}

// Split operands using comma
vector<string> splitOperands(string operandString) {
  vector<string> operands;

  string current;

  int bracketDepth = 0;

  for (char c : operandString) {
    if (c == '[')
      bracketDepth++;

    if (c == ']')
      bracketDepth--;

    if (c == ',' && bracketDepth == 0) {
      operands.push_back(trim(current));
      current.clear();
    } else {
      current += c;
    }
  }

  if (!current.empty())
    operands.push_back(trim(current));

  return operands;
}

int main(int argc, char *argv[]) {

  if(argc != 3){
    cout << "Usage: ./assembler <assembly file> <opcode file> \n>";
    return 1;
  }

  // READ OPCODE FILE
  ifstream opcodeFile(argv[2]);

  if (!opcodeFile) {
    cout << "Error: Cannot open opcode file.\n";
    return 1;
  }

  vector<string> opcodeTable;
  string line;

  while (getline(opcodeFile, line)) {
    line = trim(line);

    // Ignore empty lines
    if (line.empty())
      continue;

    // Ignore comments
    if (line[0] == '#')
      continue;

    string mnemonic;

    stringstream ss(line);

    ss >> mnemonic;

    mnemonic = toUpper(mnemonic);

    opcodeTable.push_back(mnemonic);
  }

  opcodeFile.close();


  // READ ASSEMBLY FILE

  ifstream assemblyFile(argv[1]);

  if (!assemblyFile) {
    cout << "Error: Cannot open assembly file.\n";
    return 1;
  }

  cout << "\n";

  int lineNumber = 0;

  while (getline(assemblyFile, line)) {
    lineNumber++;

    // Remove comments
    size_t commentPosition = line.find(';');

    if (commentPosition != string::npos) {
      line = line.substr(0, commentPosition);
    }

    line = trim(line);

    // Ignore empty lines
    if (line.empty())
      continue;

    // GET MNEMONIC

    string mnemonic;

    size_t spacePosition = line.find_first_of(" \t");

    string operandString;

    if (spacePosition == string::npos) {
      mnemonic = line;
    } else {
      mnemonic = line.substr(0, spacePosition);

      operandString = trim(line.substr(spacePosition + 1));
    }

    mnemonic = toUpper(mnemonic);

    // CHECK MNEMONIC

    bool exists = mnemonicExists(opcodeTable, mnemonic);

    cout << "\nLine " << lineNumber << "\n";

    cout << "Mnemonic : " << mnemonic << "\n";

    if (exists) {
      cout << "Exists   : YES\n";
    } else {
      cout << "Exists   : NO\n";
    }

    // GET OPERANDS

    if (operandString.empty()) {
      cout << "Operand  : None\n";
      cout << "Type     : None\n";

      continue;
    }

    vector<string> operands = splitOperands(operandString);

    // DISPLAY OPERANDS

    for (size_t i = 0; i < operands.size(); i++) {
      string operand = operands[i];

      string type = getOperandType(operand);

      cout << "Operand " << i + 1 << " : " << operand << "\n";

      cout << "Type     : " << type << "\n";
    }
  }

  assemblyFile.close();

  cout << "\n";

  return 0;
}
