import { useAuth } from "../context/AuthContext";

function Header() {
  const { logout, userEmail } = useAuth();

  return (
    <div className="flex justify-between items-center px-6 py-4 bg-white shadow-sm border-b border-zinc-100">
      <h1 className="text-xl font-semibold text-zinc-800">Dataset Studio</h1>

      <div className="flex items-center gap-4">
        {userEmail && (
          <span className="text-sm text-zinc-500 bg-zinc-100 px-3 py-1 rounded-full">
            {userEmail}
          </span>
        )}
        <button
          onClick={logout}
          className="bg-red-500 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-red-600 transition"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

export default Header;
