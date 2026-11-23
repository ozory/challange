import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle() {
  const { theme, setTheme, isDark, mounted } = useTheme();

  if (!mounted) {
    return (
      <button
        className="btn btn-ghost p-2"
        aria-label="Alternar tema"
        disabled
      >
        <Monitor className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
        className="btn btn-ghost p-2 relative"
        aria-label={isDark ? 'Alternar para tema claro' : 'Alternar para tema escuro'}
        title={isDark ? 'Tema escuro' : 'Tema claro'}
      >
        {isDark ? (
          <Moon className="w-5 h-5 text-yellow-400" />
        ) : (
          <Sun className="w-5 h-5 text-orange-400" />
        )}
      </button>
      
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs font-medium text-white bg-gray-900 rounded opacity-0 invisible transition-all duration-200 whitespace-nowrap pointer-events-none">
        {isDark ? 'Tema escuro' : 'Tema claro'}
      </div>
    </div>
  );
}