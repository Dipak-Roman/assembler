#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <cctype>

using namespace std;


// ============================================================
// DATA STRUCTURES
// ============================================================

struct OpcodeRule
{
    string mnemonic;
    int operandCount;

    string operand1;
    string operand2;
};


struct AssemblyLine
{
    int lineNumber;
    string text;
};


struct Operand
{
    string text;
    string type;
};


struct ParsedInstruction
{
    string mnemonic;
    vector<Operand> operands;
    int lineNumber;
};


// ============================================================
// REGISTER TABLE
// ============================================================

unordered_set<string> registers =
{
    "EAX",
    "EBX",
    "ECX",
    "EDX",
    "ESI",
    "EDI",
    "ESP",
    "EBP"
};


// ============================================================
// STRING FUNCTIONS
// ============================================================

string trim(const string& str)
{
    size_t start = str.find_first_not_of(" \t\r\n");

    if (start == string::npos)
        return "";

    size_t end = str.find_last_not_of(" \t\r\n");

    return str.substr(start, end - start + 1);
}


string toUpperCase(string str)
{
    transform(
        str.begin(),
        str.end(),
        str.begin(),
        [](unsigned char c)
        {
            return static_cast<char>(toupper(c));
        }
    );

    return str;
}


// ============================================================
// LOAD OPCODE.TXT
// ============================================================

bool loadOpcodeTable(
    const string& filename,
    vector<OpcodeRule>& opcodeTable
)
{
    ifstream file(filename);

    if (!file)
    {
        cerr << "ERROR: Cannot open opcode file: "
             << filename << '\n';

        return false;
    }

    string line;

    int lineNumber = 0;

    while (getline(file, line))
    {
        lineNumber++;

        line = trim(line);

        // Ignore empty lines
        if (line.empty())
            continue;

        // Ignore comments
        if (line[0] == '#')
            continue;


        // ----------------------------------------------------
        // Extract columns
        // ----------------------------------------------------

        stringstream ss(line);

        OpcodeRule rule;

        ss >> rule.mnemonic;
        ss >> rule.operandCount;

        if (rule.operandCount >= 1)
            ss >> rule.operand1;

        if (rule.operandCount >= 2)
            ss >> rule.operand2;


        // Convert mnemonic/types to uppercase
        rule.mnemonic = toUpperCase(rule.mnemonic);
        rule.operand1 = toUpperCase(rule.operand1);
        rule.operand2 = toUpperCase(rule.operand2);


        opcodeTable.push_back(rule);
    }

    file.close();

    return true;
}


// ============================================================
// CHECK REGISTER
// ============================================================

bool isRegister(const string& text)
{
    string value = toUpperCase(trim(text));

    return registers.find(value) != registers.end();
}


// ============================================================
// CHECK NUMBER
// ============================================================

bool isNumber(const string& text)
{
    string value = trim(text);

    if (value.empty())
        return false;


    size_t start = 0;


    // Negative number
    if (value[0] == '-')
    {
        start = 1;

        if (start == value.size())
            return false;
    }


    // Decimal
    for (size_t i = start; i < value.size(); i++)
    {
        if (!isdigit(
                static_cast<unsigned char>(value[i])))
        {
            return false;
        }
    }

    return true;
}


// ============================================================
// CHECK MEMORY OPERAND
// ============================================================

bool isMemoryOperand(const string& text)
{
    string value = trim(text);

    if (value.size() < 2)
        return false;

    if (value.front() != '[')
        return false;

    if (value.back() != ']')
        return false;

    return true;
}


// ============================================================
// CHECK LABEL
// ============================================================

bool isLabel(const string& text)
{
    string value = trim(text);

    if (value.empty())
        return false;


    // First character must be letter or _
    if (!(isalpha(
              static_cast<unsigned char>(value[0]))
          || value[0] == '_'))
    {
        return false;
    }


    for (char c : value)
    {
        if (!(isalnum(
                  static_cast<unsigned char>(c))
              || c == '_'))
        {
            return false;
        }
    }

    return true;
}


// ============================================================
// IDENTIFY OPERAND TYPE
// ============================================================

string getOperandType(const string& operand)
{
    string value = trim(operand);


    if (isRegister(value))
        return "REG";


    if (isNumber(value))
        return "IMM";


    if (isMemoryOperand(value))
        return "MEM";


    if (isLabel(value))
        return "LABEL";


    return "INVALID";
}


// ============================================================
// SPLIT OPERANDS
// ============================================================

vector<string> splitOperands(
    const string& operandText
)
{
    vector<string> operands;

    string current;

    int bracketDepth = 0;


    for (char c : operandText)
    {
        if (c == '[')
        {
            bracketDepth++;

            current += c;
        }

        else if (c == ']')
        {
            bracketDepth--;

            current += c;
        }

        else if (c == ',' && bracketDepth == 0)
        {
            operands.push_back(
                trim(current)
            );

            current.clear();
        }

        else
        {
            current += c;
        }
    }


    if (!trim(current).empty())
    {
        operands.push_back(
            trim(current)
        );
    }


    return operands;
}


// ============================================================
// PARSE ONE ASSEMBLY LINE
// ============================================================

bool parseLine(
    const AssemblyLine& line,
    ParsedInstruction& instruction,
    string& error
)
{
    string text = line.text;


    // --------------------------------------------------------
    // Remove # comments
    // --------------------------------------------------------

    size_t commentPosition = text.find('#');

    if (commentPosition != string::npos)
    {
        text = text.substr(
            0,
            commentPosition
        );
    }


    text = trim(text);


    // Empty line
    if (text.empty())
        return false;


    // --------------------------------------------------------
    // Extract mnemonic
    // --------------------------------------------------------

    stringstream ss(text);

    string mnemonic;

    ss >> mnemonic;

    mnemonic = toUpperCase(mnemonic);


    if (mnemonic.empty())
        return false;


    // --------------------------------------------------------
    // Extract operand section
    // --------------------------------------------------------

    string operandText;

    getline(ss, operandText);

    operandText = trim(operandText);


    // --------------------------------------------------------
    // Split operands
    // --------------------------------------------------------

    vector<string> operandStrings;


    if (!operandText.empty())
    {
        operandStrings =
            splitOperands(operandText);
    }


    // --------------------------------------------------------
    // Create instruction
    // --------------------------------------------------------

    instruction.mnemonic = mnemonic;

    instruction.lineNumber =
        line.lineNumber;


    // --------------------------------------------------------
    // Parse operands
    // --------------------------------------------------------

    for (const string& operandText :
         operandStrings)
    {
        string type =
            getOperandType(operandText);


        if (type == "INVALID")
        {
            error =
                "Invalid operand: " +
                operandText;

            return false;
        }


        Operand operand;

        operand.text = operandText;
        operand.type = type;


        instruction.operands.push_back(
            operand
        );
    }


    return true;
}


// ============================================================
// CHECK IF INSTRUCTION EXISTS
// ============================================================

bool instructionExists(
    const string& mnemonic,
    const vector<OpcodeRule>& opcodeTable
)
{
    for (const auto& rule : opcodeTable)
    {
        if (rule.mnemonic == mnemonic)
            return true;
    }

    return false;
}


// ============================================================
// CHECK INSTRUCTION AGAINST OPCODE TABLE
// ============================================================

bool validateInstruction(
    const ParsedInstruction& instruction,
    const vector<OpcodeRule>& opcodeTable,
    string& error
)
{
    string mnemonic =
        instruction.mnemonic;


    int operandCount =
        instruction.operands.size();


    // --------------------------------------------------------
    // Check mnemonic
    // --------------------------------------------------------

    if (!instructionExists(
            mnemonic,
            opcodeTable))
    {
        error =
            "Unknown instruction: " +
            mnemonic;

        return false;
    }


    // --------------------------------------------------------
    // Search matching rule
    // --------------------------------------------------------

    for (const auto& rule :
         opcodeTable)
    {
        if (rule.mnemonic != mnemonic)
            continue;


        // Check operand count
        if (rule.operandCount != operandCount)
            continue;


        // ----------------------------------------------------
        // One operand instruction
        // ----------------------------------------------------

        if (operandCount == 1)
        {
            if (rule.operand1 ==
                instruction.operands[0].type)
            {
                return true;
            }
        }


        // ----------------------------------------------------
        // Two operand instruction
        // ----------------------------------------------------

        if (operandCount == 2)
        {
            if (rule.operand1 ==
                    instruction.operands[0].type
                &&
                rule.operand2 ==
                    instruction.operands[1].type)
            {
                return true;
            }
        }
    }


    // --------------------------------------------------------
    // Generate useful error
    // --------------------------------------------------------

    error =
        "Invalid operand combination for " +
        mnemonic +
        ": ";


    for (size_t i = 0;
         i < instruction.operands.size();
         i++)
    {
        if (i > 0)
            error += ", ";

        error +=
            instruction.operands[i].type;
    }


    return false;
}


// ============================================================
// MAIN
// ============================================================

int main(int argc, char* argv[])
{
    // --------------------------------------------------------
    // Check arguments
    // --------------------------------------------------------

    if (argc != 3)
    {
        cout
            << "Usage:\n"
            << "./assembler test.asm opcode.txt\n";

        return 1;
    }


    string assemblyFile = argv[1];

    string opcodeFile = argv[2];


    // --------------------------------------------------------
    // Load opcode table
    // --------------------------------------------------------

    vector<OpcodeRule> opcodeTable;


    if (!loadOpcodeTable(
            opcodeFile,
            opcodeTable))
    {
        return 1;
    }


    cout
        << "Loaded "
        << opcodeTable.size()
        << " instruction rules.\n\n";


    // --------------------------------------------------------
    // Open assembly file
    // --------------------------------------------------------

    ifstream file(assemblyFile);


    if (!file)
    {
        cerr
            << "ERROR: Cannot open assembly file: "
            << assemblyFile
            << '\n';

        return 1;
    }


    string line;

    int lineNumber = 0;


    // --------------------------------------------------------
    // Read assembly file
    // --------------------------------------------------------

    while (getline(file, line))
    {
        lineNumber++;


        AssemblyLine assemblyLine;

        assemblyLine.lineNumber =
            lineNumber;

        assemblyLine.text = line;


        // ----------------------------------------------------
        // Remove # comments to check empty line
        // ----------------------------------------------------

        string checkLine = line;

        size_t commentPosition =
            checkLine.find('#');


        if (commentPosition !=
            string::npos)
        {
            checkLine =
                checkLine.substr(
                    0,
                    commentPosition
                );
        }


        if (trim(checkLine).empty())
            continue;


        // ----------------------------------------------------
        // Parse
        // ----------------------------------------------------

        ParsedInstruction instruction;

        string error;


        bool parsed =
            parseLine(
                assemblyLine,
                instruction,
                error
            );


        if (!parsed)
        {
            cout
                << "Line "
                << lineNumber
                << ": ERROR - "
                << error
                << '\n';

            continue;
        }


        // ----------------------------------------------------
        // Validate
        // ----------------------------------------------------

        bool valid =
            validateInstruction(
                instruction,
                opcodeTable,
                error
            );


        if (valid)
        {
            cout
                << "Line "
                << lineNumber
                << ": VALID - "
                << instruction.mnemonic;


            for (const auto& operand :
                 instruction.operands)
            {
                cout
                    << " ["
                    << operand.type
                    << ": "
                    << operand.text
                    << "]";
            }


            cout << '\n';
        }

        else
        {
            cout
                << "Line "
                << lineNumber
                << ": ERROR - "
                << error
                << '\n';
        }
    }


    file.close();


    return 0;
}
