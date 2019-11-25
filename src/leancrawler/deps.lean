import meta.expr

open tactic declaration environment

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

meta def print_item_crawl (env : environment) (decl : declaration) : tactic unit :=
let name := decl.to_name in
let pos := pos_line (env.decl_pos name) in
do
   if env.is_constructor name ∨ env.is_recursor name then return () else do
   trace ("- Name: " ++ to_string decl.to_name),
   trace ("  Line: " ++ pos),
   match decl with
   | (thm _ _ _ _) := do
      proofs ← (list_items decl.value).mfilter $ λ c, mk_const c >>= is_proof,
      others ← (list_items decl.value).mfilter $ λ c, mk_const c >>= is_proof >>= mnot,
      trace  "  Type: theorem",
      trace ("  Statement uses: " ++ (to_string $ list_items decl.type)),
      trace ("  Size: " ++ (to_string $ sizeof $ to_string decl.type)),
      trace ("  Proof uses lemmas: " ++ to_string proofs),
      trace ("  and uses: " ++ to_string others),
      trace ("  Proof size: " ++ (to_string $ sizeof $ to_string decl.value))
  | (defn _ _ _ _ _ _) := do
      tactic.has_attribute `instance name >> (do tactic.trace "  Type: instance",
        trace $ "  Target: " ++ to_string decl.type.get_pi_app_fn)   <|>
        match env.is_projection name with
        | some info := do trace "  Type: structure_field", trace $ "  Parent: " ++ to_string info.cname
        | none :=  trace  "  Type: definition"
        end,
      trace ("  Uses: " ++ (to_string $ list_items decl.type ++ list_items decl.value)),
      trace ("  Size: " ++ (to_string $ sizeof $ to_string decl.value))

  | (cnst _ _ _ _) := do
      (tactic.has_attribute `class name >> do
        tactic.trace "  Type: class",
        match env.structure_fields name with
        | some l := do tactic.trace $ "  Fields: " ++ (to_string l)
        | none   := do tactic.trace ("  Fields: None")
        end) <|>
      match env.structure_fields name with
      | some l := do trace "  Type: structure", trace $"  Fields: " ++ (to_string l)
      | none   := do if is_ginductive env name then trace "  Type: inductive" else
                     trace ("  Type: constant")
      end,
      trace ("  Size: " ++ (to_string $ sizeof $ to_string decl.value))
  | (ax _ _ _) := do
      trace ("  Type: axiom"),
      trace ("  Uses: " ++ (to_string $ list_items decl.type)),
      trace ("  Size: " ++ (to_string $ sizeof $ to_string decl.value))
  end

meta def print_content : tactic unit :=
do curr_env ← get_env,
   let decls := curr_env.fold [] list.cons,
   let local_decls := decls.filter
     (λ x, environment.in_current_file' curr_env (to_name x) && not (to_name x).is_internal),
   local_decls.mmap' (print_item_crawl curr_env)
