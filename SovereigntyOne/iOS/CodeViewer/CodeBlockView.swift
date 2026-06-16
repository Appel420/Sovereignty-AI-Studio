import SwiftUI
import Splash

struct CodeBlockView: View {
    let configuration: CodeBlockConfiguration
    let language: String
    let colorScheme: ColorScheme
    
    @State private var highlightedLine: Int? = nil
    @State private var searchText: String = ""
    @State private var showCopyToast: Bool = false
    
    private var lines: [String] {
        configuration.content.components(separatedBy: .newlines)
    }
    
    private var filteredLines: [(index: Int, line: String)] {
        if searchText.isEmpty {
            return Array(lines.enumerated()).map { ($0.offset, $0.element) }
        } else {
            return lines.enumerated()
                .filter { $0.element.localizedCaseInsensitiveContains(searchText) }
                .map { ($0.offset, $0.element) }
        }
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header with smart copy button
            HStack {
                Text(language.uppercased())
                    .font(.caption.bold())
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Button {
                    copyVisibleContent()
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "doc.on.doc")
                        Text(searchText.isEmpty ? "Copy All" : "Copy Filtered")
                            .font(.caption)
                    }
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color(.tertiarySystemBackground))
            
            Divider()
            
            // Search
            HStack {
                Image(systemName: "magnifyingglass")
                TextField("Search code...", text: $searchText)
                    .textFieldStyle(.plain)
                if !searchText.isEmpty {
                    Button("Clear") { searchText = "" }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            
            Divider()
            
            ScrollView(.vertical) {
                HStack(alignment: .top, spacing: 0) {
                    // Fixed Line Numbers
                    VStack(alignment: .trailing, spacing: 0) {
                        ForEach(filteredLines, id: \.index) { item in
                            Button {
                                highlightedLine = item.index
                                UIPasteboard.general.string = item.line
                            } label: {
                                Text("\(item.index + 1)")
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundColor(.secondary)
                                    .frame(minWidth: 34, alignment: .trailing)
                                    .padding(.trailing, 10)
                                    .padding(.vertical, 3)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .background(Color(.secondarySystemBackground).opacity(0.6))
                    
                    // Horizontally scrollable highlighted code
                    ScrollView(.horizontal) {
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(filteredLines, id: \.index) { item in
                                Text(item.line.isEmpty ? " " : item.line)
                                    .font(.system(.body, design: .monospaced))
                                    .textSelection(.enabled)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 3)
                                    .background(highlightedLine == item.index ? Color.blue.opacity(0.15) : Color.clear)
                            }
                        }
                    }
                }
            }
        }
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
    
    private func copyVisibleContent() {
        let text = searchText.isEmpty 
            ? configuration.content 
            : filteredLines.map { $0.line }.joined(separator: "\n")
        UIPasteboard.general.string = text
        // Toast logic would go here
    }
}