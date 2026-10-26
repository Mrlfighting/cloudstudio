/** 只追踪拼豆发起的确认框；换号即关闭，避免旧账号名称和操作残留。 */
import { ref } from "vue";
import { ElMessageBox } from "element-plus";
export const beadDialogDepth = ref(0);
async function tracked<T>(show: () => Promise<T>): Promise<T> {
  beadDialogDepth.value++;
  try {
    return await show();
  } finally {
    beadDialogDepth.value--;
  }
}
export const beadMessageBox = {
  confirm: (...args: Parameters<typeof ElMessageBox.confirm>) =>
    tracked(() => ElMessageBox.confirm(...args)),
  prompt: (...args: Parameters<typeof ElMessageBox.prompt>) =>
    tracked(() => ElMessageBox.prompt(...args)),
};
export function cancelBeadDialogs(): void {
  if (beadDialogDepth.value > 0) ElMessageBox.close();
}
