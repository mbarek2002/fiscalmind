from backend.app.evaluation.ragas_eval import run_ragas_evaluation


def main() -> None:
	result, agent_results = run_ragas_evaluation()

	print(f"{len(agent_results)} questions evaluees\n")
	print(result)
	print()

	df = result.to_pandas()
	for _, row in df.iterrows():
		print(f"- Q: {row['user_input'][:80]}")
		print(f"  faithfulness={row.get('faithfulness')} answer_relevancy={row.get('answer_relevancy')}")


if __name__ == "__main__":
	main()
