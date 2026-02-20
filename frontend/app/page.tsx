export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
          Medrix
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          AI-Powered Medical History Management
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12 max-w-4xl">
          <div className="p-6 border rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-2xl font-semibold mb-2">📄 Smart Upload</h2>
            <p className="text-gray-600">
              Upload medical documents and let AI extract structured data automatically
            </p>
          </div>
          <div className="p-6 border rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-2xl font-semibold mb-2">📊 Timeline</h2>
            <p className="text-gray-600">
              Visualize your complete medical history chronologically
            </p>
          </div>
          <div className="p-6 border rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-2xl font-semibold mb-2">🔍 Smart Search</h2>
            <p className="text-gray-600">
              Ask questions and get answers with citations from your records
            </p>
          </div>
          <div className="p-6 border rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <h2 className="text-2xl font-semibold mb-2">💳 Medical ID</h2>
            <p className="text-gray-600">
              Generate portable summary cards for emergencies
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
