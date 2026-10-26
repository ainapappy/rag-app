<script setup lang="ts">
import { CollapsibleContent, CollapsibleRoot, CollapsibleTrigger } from "reka-ui";
import type { Source } from "@/types/chat";

defineProps<{ sources: Source[] }>();
</script>

<template>
  <CollapsibleRoot class="mt-2 block">
    <CollapsibleTrigger
      class="cursor-pointer text-xs font-medium text-slate-500 underline underline-offset-2 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
    >
      Sources ({{ sources.length }})
    </CollapsibleTrigger>
    <CollapsibleContent class="mt-2 space-y-2">
      <div
        v-for="(source, index) in sources"
        :key="`${source.source}-${source.page}-${index}`"
        class="rounded-lg border border-slate-200 bg-white p-2 text-xs dark:border-slate-700 dark:bg-slate-900"
      >
        <div class="flex items-center justify-between gap-2 font-medium">
          <span class="truncate">{{ source.source }}</span>
          <span class="shrink-0 text-slate-500 dark:text-slate-400">
            page {{ source.page ?? "—" }} · score {{ source.score.toFixed(2) }}
          </span>
        </div>
        <p class="mt-1 text-slate-600 dark:text-slate-300">{{ source.excerpt }}</p>
      </div>
    </CollapsibleContent>
  </CollapsibleRoot>
</template>
