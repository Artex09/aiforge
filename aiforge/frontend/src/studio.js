import { createContext, useContext } from "react";

// Lets custom React Flow nodes reach the app's node actions without prop-drilling
// through the reactflow renderer.
export const StudioContext = createContext({
  onEdit: () => {},
  onDuplicate: () => {},
  onDelete: () => {},
});

export const useStudio = () => useContext(StudioContext);
