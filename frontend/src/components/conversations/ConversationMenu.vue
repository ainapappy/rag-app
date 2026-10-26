<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger,
} from "reka-ui";

defineEmits<{ remove: [] }>();
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger
      aria-label="Actions de la conversation"
      class="cursor-pointer rounded p-1 text-slate-400 opacity-0 transition group-hover:opacity-100 hover:text-slate-700 focus-visible:opacity-100 dark:hover:text-slate-200"
    >
      ⋯
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        align="end"
        :side-offset="4"
        class="z-50 min-w-32 rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg dark:border-slate-800 dark:bg-slate-900"
      >
        <DropdownMenuItem
          class="cursor-pointer px-3 py-1.5 text-red-600 outline-none data-[highlighted]:bg-red-50 dark:text-red-400 dark:data-[highlighted]:bg-red-950"
          @select="$emit('remove')"
        >
          Supprimer…
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
