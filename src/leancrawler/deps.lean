import meta.expr

namespace level
meta def size : level → ℕ
| (succ l)     := size l + 1
| (max l₁ l₂)  := size l₁ + size l₂ + 1
| (imax l₁ l₂) := size l₁ + size l₂ + 1
| _            := 1

meta def dedup_size_aux : level → state (native.rb_set level) ℕ | l := do
  s ← get,
  if s.contains l then return 1 else
  match l with
  | (succ l)     := do
    n ← dedup_size_aux l,
    return (n + 1)
  | (max l₁ l₂)  := do
    n₁ ← dedup_size_aux l₁,
    n₂ ← dedup_size_aux l₂,
    return (n₁ + n₂ + 1)
  | (imax l₁ l₂) := do
    n₁ ← dedup_size_aux l₁,
    n₂ ← dedup_size_aux l₂,
    return (n₁ + n₂ + 1)
  | l            := return 1
  end <* modify (λ s, s.insert l)

meta def dedup_size (l : level) : ℕ :=
prod.fst $ (dedup_size_aux l).run $
@native.mk_rb_set _ ⟨λ a b : level, a.lt b⟩ _

end level

namespace expr
meta def size : expr → ℕ
| (var n) := 1
| (sort l) := l.size + 1
| (const n ls) := list.sum (level.size <$> ls) + 1
| (mvar n m t)   := size t + 1
| (local_const n m bi t) := size t + 1
| (app e f) := size e + size f + 1
| (lam n bi e t) := size e + size t + 1
| (pi n bi e t) := size e + size t + 1
| (elet n g e f) := size g + size e + size f + 1
| (macro d args) := list.sum (size <$> args) + 1

meta def lift {α} : state (native.rb_set level) α → state (native.rb_set level × native.rb_set expr) α
| ⟨f⟩ := ⟨λ ⟨s, t⟩, let ⟨a, s'⟩ := f s in ⟨a, s', t⟩⟩

meta def dedup_size_aux : expr → state (native.rb_set level × native.rb_set expr) ℕ
| e := do
  s ← get,
  if s.2.contains e then return 1 else
  match e with
  | (sort l) := do
    n ← lift l.dedup_size_aux,
    return (n + 1)
  | (const n ls) := do
    ns ← list.traverse (lift ∘ level.dedup_size_aux) ls,
    return (list.sum ns + 1)
  | (mvar n m t) := do
    n ← t.dedup_size_aux,
    return (n + 1)
  | (local_const n m bi t) := do
    n ← t.dedup_size_aux,
    return (n + 1)
  | (app e f) := do
    n₁ ← e.dedup_size_aux,
    n₂ ← f.dedup_size_aux,
    return (n₁ + n₂ + 1)
  | (lam n bi e t) := do
    n₁ ← e.dedup_size_aux,
    n₂ ← t.dedup_size_aux,
    return (n₁ + n₂ + 1)
  | (pi n bi e t) := do
    n₁ ← e.dedup_size_aux,
    n₂ ← t.dedup_size_aux,
    return (n₁ + n₂ + 1)
  | (elet n g e f) := do
    n₁ ← g.dedup_size_aux,
    n₂ ← e.dedup_size_aux,
    n₃  ← f.dedup_size_aux,
    return (n₁ + n₂ + n₃ + 1)
  | (macro d args) := do
    ns ← list.traverse dedup_size_aux args,
    return (list.sum ns + 1)
  | _ := return 1
  end <* modify (λ ⟨s₁, s₂⟩, ⟨s₁, s₂.insert e⟩)

meta def dedup_size (e : expr) : ℕ :=
prod.fst $ (dedup_size_aux e).run
(@native.mk_rb_set _ ⟨λ a b : level, a.lt b⟩ _,
 @native.mk_rb_set _ ⟨λ a b : expr, a.lt b⟩ _)
end expr

open tactic declaration environment

-- The next instance is there to prevent PyYAML trying to be too smart
meta def my_name_to_string : has_to_string name :=
⟨λ n, "\"" ++ to_string n ++ "\""⟩

local attribute [instance] my_name_to_string

meta def expr.get_pi_app_fn : expr → expr
| (expr.pi _ _ _ e) := e.get_pi_app_fn
| e                 := e.get_app_fn

meta def list_items (e : expr) : list name :=
e.fold [] $ λ e _ cs,
if e.is_constant ∧ ¬ e.const_name ∈ cs
  then e.const_name :: cs
  else cs

meta def mnot : bool → tactic bool := λ p, return (¬ p)

meta def pos_line (p : option pos) : string :=
match p with
| some x := to_string x.line
| _      := ""
end

meta def file_name (p : option string) : string :=
match p with
| some x := x
| _      := "Unknown file"
end

section

structure declaration.modifiers :=
(Class := ff)
(Structure := ff)
(StructureField := ff)
(Inductive := ff)
(Instance := ff)
(IsRecursor := ff)
(IsConstructor := ff)

def bool.to_string_python : has_to_string bool := ⟨λ k, match k with tt := "True" | ff := "False" end⟩
local attribute [instance] bool.to_string_python

instance : has_to_string declaration.modifiers := ⟨λ m,
  "{ class: " ++ to_string m.Class ++
  ", structure: " ++ to_string m.Structure ++
  ", structure_field: " ++ to_string m.StructureField ++
  ", is_recursor: " ++ to_string m.IsRecursor ++
  ", is_constructor: " ++ to_string m.IsConstructor ++
  ", inductive: " ++ to_string m.Inductive ++
  ", instance: " ++ to_string m.Instance ++ " }"⟩

open  tactic declaration environment

meta def declaration.get_kind_string : declaration → string
| (thm _ _ _ _) := "lemma"
| (defn _ _ _ _ _ _) := "definition"
| (cnst _ _ _ _) := "constant"
| (ax _ _ _) := "axiom"


meta def environment.get_modifiers (env : environment) (n : name) : tactic declaration.modifiers :=
do
  c ← (has_attribute `class n >> return tt) <|> return ff,
  i ← (has_attribute `instance n >> return tt) <|> return ff,
  return {
    Class := c,
    Structure := env.is_structure n,
    StructureField := (env.is_projection n).is_some,
    IsConstructor := env.is_constructor n,
    IsRecursor := env.is_recursor n,
    Inductive := env.is_ginductive n,
    Instance := i }
end

meta def print_item_crawl (env : environment) (decl : declaration) : tactic unit :=
let name := decl.to_name,
    pos := pos_line (env.decl_pos name),
    fname := file_name (env.decl_olean name) in
do
   trace ("- Name: " ++ to_string name),
   trace ("  File: " ++ fname),
   trace ("  Line: " ++ pos),
   trace ("  Kind: " ++ decl.get_kind_string),
   mods ← env.get_modifiers name,
   trace ("  Modifiers: " ++ to_string mods),

   pp_type ← pp decl.type,
   trace ("  Type: " ++ (to_string pp_type).quote),
   type_proofs ← (list_items decl.type).mfilter $ λ c, mk_const c >>= is_proof,
   type_others ← (list_items decl.type).mfilter $ λ c, mk_const c >>= is_proof >>= mnot,
   trace ("  Type uses proofs: " ++ to_string type_proofs),
   trace ("  Type uses others: " ++ to_string type_others),
   trace ("  Type size: " ++ to_string decl.type.size),
   trace ("  Type dedup size: " ++ to_string decl.type.dedup_size),
   trace ("  Type pp size: " ++ (to_string $ sizeof $ to_string pp_type)),

   pp_value ← pp decl.value,
   trace ("  Value: " ++ (to_string pp_value).quote),
   value_proofs ← (list_items decl.value).mfilter $ λ c, mk_const c >>= is_proof,
   value_others ← (list_items decl.value).mfilter $ λ c, mk_const c >>= is_proof >>= mnot,
   trace ("  Value uses proofs: " ++ to_string value_proofs),
   trace ("  Value uses others: " ++ to_string value_others),
   trace ("  Value size: " ++ to_string decl.value.size),
   trace ("  Value dedup size: " ++ to_string decl.value.dedup_size),
   trace ("  Value pp size: " ++ (to_string $ sizeof $ to_string pp_value)),

   trace ("  Target class: " ++ if mods.Instance then to_string decl.type.get_pi_app_fn else ""),
   trace ("  Parent: " ++  match env.is_projection name with
                           | some info := to_string info.cname
                           | none :=  ""
                           end),
   trace ("  Fields: " ++ (to_string $ (env.structure_fields_full name).get_or_else []))

meta def print_name (n : name): tactic unit :=
do curr_env ← get_env,
   decl ← curr_env.get n,
   print_item_crawl curr_env decl

meta def print_content : tactic unit :=
do curr_env ← get_env,
   let decls := curr_env.fold [] list.cons,
   let local_decls := decls.filter
     (λ x, environment.in_current_file curr_env (to_name x) && not (to_name x).is_internal),
   local_decls.mmap' (print_item_crawl curr_env)

meta def print_all_content : tactic unit :=
do curr_env ← get_env,
   let decls := curr_env.fold [] list.cons,
   let local_decls := decls.filter
     (λ x, not (to_name x).is_internal),
   local_decls.mmap' (print_item_crawl curr_env)
