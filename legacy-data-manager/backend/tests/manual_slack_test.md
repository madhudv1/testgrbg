# Manual Slack Integration Test Plan

## Prerequisites
- [ ] ngrok is running (`ngrok http 8000`)
- [ ] Slack app webhook URLs updated with ngrok URL
- [ ] Backend server is running
- [ ] Test Google Drive folder is accessible

## 1. Basic Command Testing

### Help Command
```
/testlegacy help
```
Expected Response:
- [ ] Shows formatted message with sections
- [ ] Lists all available commands
- [ ] Proper formatting (bold headers, bullet points)
- [ ] All commands are current and correct

### Status Command
```
/testlegacy status
```
Expected Response:
- [ ] Shows Health Score (0-100)
- [ ] Lists urgent items if present
- [ ] "View Details" button links to dashboard
- [ ] Emojis render correctly (🏥, 🔒, 📅, 💾)
- [ ] Health score calculation appears reasonable

### List Command
```
/testlegacy list
```
Expected Response:
- [ ] Shows "Available Directories 📁" header
- [ ] Lists actual directories from drive
- [ ] Clean bullet-point formatting
- [ ] No authentication errors

## 2. Analysis Commands

### Analyze Directory
```
# Test with valid directory
/testlegacy analyze TestFolder

# Test with non-existent directory
/testlegacy analyze NonExistentFolder
```
Expected Response (Valid Directory):
- [ ] Shows total files count
- [ ] Shows sensitive files count
- [ ] Shows old files count
- [ ] Lists key findings
- [ ] "View Detailed Analysis" button works
- [ ] Dashboard URL is correct

Expected Response (Invalid Directory):
- [ ] Shows clear error message
- [ ] Suggests checking directory name
- [ ] Error is ephemeral (only visible to user)

### Summary Command
```
/testlegacy summary TestFolder
```
Expected Response:
- [ ] Shows total files
- [ ] Shows storage used
- [ ] Lists file categories
- [ ] "Open Dashboard" button works
- [ ] All numbers are properly formatted

### Risk Analysis
```
/testlegacy risks TestFolder
```
Expected Response:
- [ ] Shows risk summary
- [ ] Lists sensitive file count
- [ ] Shows risk levels (High/Medium/Low)
- [ ] Lists top concerns
- [ ] "View Details" button links correctly

## 3. Error Cases

### Missing Arguments
```
/testlegacy analyze
/testlegacy risks
```
Expected Response:
- [ ] Shows usage hint
- [ ] Error is ephemeral
- [ ] Message is helpful and clear

### Invalid Commands
```
/testlegacy invalidcommand
```
Expected Response:
- [ ] Shows "Unknown command" message
- [ ] Suggests using help command
- [ ] Error is ephemeral

## 4. Edge Cases

### Long Directory Names
```
/testlegacy analyze "Very Long Directory Name With Spaces And Special Characters !@#$"
```
Expected Response:
- [ ] Handles spaces correctly
- [ ] Handles special characters
- [ ] URL encoding works properly

### Multiple Commands
```
# Run multiple commands in quick succession
/testlegacy status
/testlegacy list
/testlegacy analyze TestFolder
```
Expected Response:
- [ ] All commands process correctly
- [ ] No rate limiting issues
- [ ] Responses match correct commands

## Test Data Setup

Required Test Files:
1. Regular files (docs, sheets)
2. Old files (>3 years)
3. Files with sensitive content
4. Files in nested directories

Test Directory Structure:
```
TestFolder/
├── OldFiles/
│   ├── old_document.docx (>3 years)
│   └── old_spreadsheet.xlsx (>3 years)
├── SensitiveFiles/
│   ├── pii_data.xlsx
│   └── financial_report.pdf
└── RegularFiles/
    ├── recent_doc.docx
    └── presentation.pptx
```

## Notes
- Document any unexpected behavior
- Note response times for each command
- Record any error messages exactly as shown
- Document any UI/formatting issues 