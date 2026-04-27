import { useState } from "react";
import CollapsibleSection from "./CollapsibleSection";
import styles from "../styles/RecipesSection.module.css";

export default function RecipesSection({ recetas: initial }) {
  const [recipes, setRecipes] = useState(initial || []);
  const [expandedId, setExpandedId] = useState(null);
  const [newRecipe, setNewRecipe] = useState({ name: "", servings: 2 });
  const [newIngs, setNewIngs] = useState({});
  const [editingCell, setEditingCell] = useState(null);
  const [editValue, setEditValue] = useState("");

  function getNewIng(recipeId) {
    return newIngs[recipeId] || { item: "", quantity: "", unit: "" };
  }

  function patchNewIng(recipeId, patch) {
    setNewIngs(prev => ({
      ...prev,
      [recipeId]: { ...getNewIng(recipeId), ...patch },
    }));
  }

  async function handleAddRecipe(e) {
    e.preventDefault();
    if (!newRecipe.name.trim()) return;
    const res = await fetch("/api/dashboard/recipes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newRecipe),
    });
    if (!res.ok) return;
    const { id } = await res.json();
    setRecipes(prev => [
      ...prev,
      { id, name: newRecipe.name.trim(), servings: newRecipe.servings, ingredients: [] },
    ]);
    setNewRecipe({ name: "", servings: 2 });
  }

  async function handleDeleteRecipe(id) {
    const snapshot = recipes;
    setRecipes(prev => prev.filter(r => r.id !== id));
    if (expandedId === id) setExpandedId(null);
    const res = await fetch(`/api/dashboard/recipes/${id}`, { method: "DELETE" });
    if (!res.ok) setRecipes(snapshot);
  }

  async function handleAddIngredient(recipeId) {
    const ing = getNewIng(recipeId);
    if (!ing.item.trim()) return;
    const body = {
      item: ing.item.trim(),
      quantity: ing.quantity !== "" ? parseFloat(ing.quantity) : null,
      unit: ing.unit.trim() || null,
    };
    const res = await fetch(`/api/dashboard/recipes/${recipeId}/ingredients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return;
    const { id } = await res.json();
    setRecipes(prev => prev.map(r =>
      r.id === recipeId
        ? { ...r, ingredients: [...r.ingredients, { id, ...body }] }
        : r
    ));
    setNewIngs(prev => ({ ...prev, [recipeId]: { item: "", quantity: "", unit: "" } }));
  }

  async function handleDeleteIngredient(recipeId, ingId) {
    const snapshot = recipes;
    setRecipes(prev => prev.map(r =>
      r.id === recipeId
        ? { ...r, ingredients: r.ingredients.filter(i => i.id !== ingId) }
        : r
    ));
    const res = await fetch(`/api/dashboard/recipes/${recipeId}/ingredients/${ingId}`, {
      method: "DELETE",
    });
    if (!res.ok) setRecipes(snapshot);
  }

  function startEdit(ingId, field, value) {
    setEditingCell({ ingId, field });
    setEditValue(value == null ? "" : String(value));
  }

  async function commitEdit(recipeId, ingId, field) {
    setEditingCell(null);
    const snapshot = recipes;
    const raw = editValue.trim();
    const parsed = field === "quantity" ? (raw ? parseFloat(raw) : null) : (raw || null);
    setRecipes(prev => prev.map(r =>
      r.id === recipeId
        ? { ...r, ingredients: r.ingredients.map(i => i.id === ingId ? { ...i, [field]: parsed } : i) }
        : r
    ));
    const res = await fetch(`/api/dashboard/recipes/${recipeId}/ingredients/${ingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: parsed }),
    });
    if (!res.ok) setRecipes(snapshot);
  }

  function isEditing(ingId, field) {
    return editingCell?.ingId === ingId && editingCell?.field === field;
  }

  function editableCell(recipeId, ingId, field, value, placeholder, isNum) {
    if (isEditing(ingId, field)) {
      return (
        <input
          className={styles.cellInput}
          type={isNum ? "number" : "text"}
          min={isNum ? "0" : undefined}
          step={isNum ? "0.25" : undefined}
          value={editValue}
          placeholder={placeholder}
          onChange={e => setEditValue(e.target.value)}
          onBlur={() => commitEdit(recipeId, ingId, field)}
          onKeyDown={e => e.key === "Enter" && commitEdit(recipeId, ingId, field)}
          autoFocus
        />
      );
    }
    return (
      <span
        className={`${styles.cellEditable} ${!value && value !== 0 ? styles.cellEmpty : ""}`}
        onClick={() => startEdit(ingId, field, value)}
        title="Clic para editar"
      >
        {value != null && value !== "" ? value : placeholder}
      </span>
    );
  }

  return (
    <CollapsibleSection
      title="Recetas"
      description="Crea y edita tus recetas. Usa 'nueva receta: cazuela' por WhatsApp para que la IA sugiera ingredientes."
      defaultOpen={false}
    >
      {recipes.length === 0 && (
        <p className={styles.empty}>
          Sin recetas. Crea una abajo o con <em>nueva receta: cazuela</em> por WhatsApp.
        </p>
      )}

      {recipes.map(recipe => (
        <div key={recipe.id} className={styles.recipeCard}>
          <div className={styles.recipeHeader}>
            <button
              className={styles.expandBtn}
              onClick={() => setExpandedId(expandedId === recipe.id ? null : recipe.id)}
            >
              <span className={styles.recipeName}>{recipe.name}</span>
              <span className={styles.servings}>{recipe.servings} personas</span>
              <span className={styles.chevron}>{expandedId === recipe.id ? "▲" : "▼"}</span>
            </button>
            <button className={styles.deleteBtn} onClick={() => handleDeleteRecipe(recipe.id)}>×</button>
          </div>

          {expandedId === recipe.id && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Ingrediente</th>
                  <th className={styles.numCol}>Cant.</th>
                  <th className={styles.unitCol}>Unidad</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recipe.ingredients.map(ing => (
                  <tr key={ing.id}>
                    <td className={styles.ingredientName}>{editableCell(recipe.id, ing.id, "item", ing.item, "nombre", false)}</td>
                    <td className={styles.numCol}>{editableCell(recipe.id, ing.id, "quantity", ing.quantity, "—", true)}</td>
                    <td className={styles.unitCol}>{editableCell(recipe.id, ing.id, "unit", ing.unit, "—", false)}</td>
                    <td>
                      <button className={styles.deleteBtn} onClick={() => handleDeleteIngredient(recipe.id, ing.id)}>×</button>
                    </td>
                  </tr>
                ))}
                <tr className={styles.addRow}>
                  <td>
                    <input
                      className={styles.addInput}
                      placeholder="nuevo ingrediente"
                      value={getNewIng(recipe.id).item}
                      onChange={e => patchNewIng(recipe.id, { item: e.target.value })}
                      onKeyDown={e => e.key === "Enter" && handleAddIngredient(recipe.id)}
                    />
                  </td>
                  <td className={styles.numCol}>
                    <input
                      className={styles.addInput}
                      type="number"
                      min="0"
                      step="0.25"
                      placeholder="—"
                      value={getNewIng(recipe.id).quantity}
                      onChange={e => patchNewIng(recipe.id, { quantity: e.target.value })}
                    />
                  </td>
                  <td className={styles.unitCol}>
                    <input
                      className={styles.addInput}
                      placeholder="—"
                      value={getNewIng(recipe.id).unit}
                      onChange={e => patchNewIng(recipe.id, { unit: e.target.value })}
                    />
                  </td>
                  <td>
                    <button className={styles.addBtn} onClick={() => handleAddIngredient(recipe.id)}>+</button>
                  </td>
                </tr>
              </tbody>
            </table>
          )}
        </div>
      ))}

      <div className={styles.addRecipeRow}>
        <input
          className={styles.addInput}
          placeholder="nueva receta"
          value={newRecipe.name}
          onChange={e => setNewRecipe(p => ({ ...p, name: e.target.value }))}
          onKeyDown={e => e.key === "Enter" && handleAddRecipe(e)}
        />
        <input
          className={styles.servingsInput}
          type="number"
          min="1"
          value={newRecipe.servings}
          onChange={e => setNewRecipe(p => ({ ...p, servings: e.target.value === "" ? "" : parseInt(e.target.value, 10) || 1 }))}
        />
        <span className={styles.servingsLabel}>personas</span>
        <button className={styles.addBtn} onClick={handleAddRecipe}>+</button>
      </div>
    </CollapsibleSection>
  );
}
