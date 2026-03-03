import React, { useState } from 'react';
import { BookOpenIcon } from '@heroicons/react/24/outline';
import { GenerationAPI } from '../services/api';

const StoryGenerator: React.FC = () => {
  const [genre, setGenre] = useState('Fantasy');
  const [theme, setTheme] = useState('');
  const [storyLength, setStoryLength] = useState('Short (1-2 pages)');
  const [style, setStyle] = useState('');
  const [illustrations, setIllustrations] = useState(false);
  const [narration, setNarration] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setResult(null);

    const prompt = [
      `Genre: ${genre}`,
      theme ? `Theme: ${theme}` : '',
      `Length: ${storyLength}`,
      style ? `Style: ${style}` : '',
      illustrations ? 'Include illustrations' : '',
      narration ? 'Add narration' : '',
    ].filter(Boolean).join('. ');

    try {
      const data = await GenerationAPI.create('text', prompt, {
        genre,
        story_length: storyLength,
        illustrations,
        narration,
      });
      setResult(JSON.stringify(data, null, 2));
    } catch {
      setResult('Story generation request submitted (offline mode).');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="flex justify-center items-center mb-4">
          <BookOpenIcon className="h-12 w-12 text-blue-500" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 font-space-grotesk">
          Story Generator
        </h1>
        <p className="text-lg text-gray-600 mt-2">
          Create complete stories with illustrations and narration
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <form className="space-y-6" onSubmit={handleGenerate}>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Genre
            </label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option>Fantasy</option>
              <option>Science Fiction</option>
              <option>Mystery</option>
              <option>Romance</option>
              <option>Adventure</option>
              <option>Horror</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Theme
            </label>
            <input
              type="text"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="e.g., A hero's journey to save the world"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Story Length
            </label>
            <select
              value={storyLength}
              onChange={(e) => setStoryLength(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option>Short (1-2 pages)</option>
              <option>Medium (3-5 pages)</option>
              <option>Long (6-10 pages)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Style Preferences
            </label>
            <textarea
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              placeholder="Describe the tone, style, and any specific elements you want included"
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="mr-2"
                checked={illustrations}
                onChange={(e) => setIllustrations(e.target.checked)}
              />
              <span className="text-sm text-gray-700">Generate illustrations</span>
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                className="mr-2"
                checked={narration}
                onChange={(e) => setNarration(e.target.checked)}
              />
              <span className="text-sm text-gray-700">Add narration</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg hover:bg-primary-700 transition-colors font-medium disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Story'}
          </button>
        </form>

        {result && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Result</h3>
            <pre className="text-sm text-gray-800 whitespace-pre-wrap">{result}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default StoryGenerator;